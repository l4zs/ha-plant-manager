"""HTTP views for photos, identification, import and backups."""

from __future__ import annotations

from http import HTTPStatus
import os

from aiohttp import BodyPartReader, web
from homeassistant.components.http import KEY_HASS, HomeAssistantView

from .const import (
    BACKUP_URL,
    IDENTIFY_URL,
    MAX_PHOTO_BYTES,
    MAX_UPLOAD_BYTES,
    PHOTO_UPLOAD_URL,
    PHOTO_URL,
    STAGED_URL,
    UPLOAD_URL,
)
from .db import NotFoundError
from .i18n import language, translate_message
from .manager import PlantManager, get_manager


def _manager(request: web.Request) -> PlantManager | None:
    return get_manager(request.app[KEY_HASS])


def _language(request: web.Request) -> str:
    """The UI's language (the panel adds it to the URL), or Home Assistant's."""
    requested = request.query.get("language")
    if (manager := _manager(request)) is not None:
        return manager.ui_language(requested)
    return language(requested or request.app[KEY_HASS].config.language)


def _t(request: web.Request, message: str) -> str:
    return translate_message(_language(request), message)


async def _read_file(request: web.Request, limit: int) -> bytes | None:
    reader = await request.multipart()
    field = await reader.next()
    while field is not None and getattr(field, "name", None) != "file":
        field = await reader.next()
    if field is None or not isinstance(field, BodyPartReader):
        return None
    data = bytearray()
    while chunk := await field.read_chunk():
        data.extend(chunk)
        if len(data) > limit:
            raise ValueError("File too large")
    return bytes(data)


class PhotoView(HomeAssistantView):
    """Serve a stored photo. Requests carry a signed path (authSig)."""

    url = PHOTO_URL
    name = "api:plant_manager:photo"
    requires_auth = True

    async def get(self, request: web.Request, photo_id: str) -> web.StreamResponse:
        """Return the photo file."""
        if (manager := _manager(request)) is None:
            return web.Response(status=HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            path = await manager.async_photo_file(photo_id)
        except NotFoundError:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        if not await request.app[KEY_HASS].async_add_executor_job(os.path.isfile, path):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        # Photo files never change, a new upload gets a new id.
        return web.FileResponse(
            path, headers={"Cache-Control": "private, max-age=31536000, immutable"}
        )


class StagedPhotoView(HomeAssistantView):
    """Serve a photo that was taken for identification and is not saved yet."""

    url = STAGED_URL
    name = "api:plant_manager:staged"
    requires_auth = True

    async def get(self, request: web.Request, staged_id: str) -> web.StreamResponse:
        """Return the staged photo."""
        manager = _manager(request)
        path = manager.staged_path(staged_id) if manager else None
        if path is None or not await request.app[KEY_HASS].async_add_executor_job(
            os.path.isfile, path
        ):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})


class PhotoUploadView(HomeAssistantView):
    """Accept a photo upload for a plant (multipart field "file")."""

    url = PHOTO_UPLOAD_URL
    name = "api:plant_manager:photo_upload"
    requires_auth = True

    async def post(self, request: web.Request, plant_id: str) -> web.Response:
        """Store the uploaded image."""
        if (manager := _manager(request)) is None:
            return self.json_message(_t(request, "Not loaded"), HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            data = await _read_file(request, MAX_PHOTO_BYTES)
        except ValueError as err:
            return self.json_message(_t(request, str(err)), HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if data is None:
            return self.json_message(_t(request, "Missing file"), HTTPStatus.BAD_REQUEST)
        try:
            photo = await manager.async_add_photo(plant_id, data, "upload")
        except NotFoundError:
            return self.json_message(_t(request, "Plant not found"), HTTPStatus.NOT_FOUND)
        except ValueError as err:
            return self.json_message(_t(request, str(err)), HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        return self.json({"id": photo["id"]})


class IdentifyView(HomeAssistantView):
    """Identify the plant in an uploaded photo. The photo is staged for saving."""

    url = IDENTIFY_URL
    name = "api:plant_manager:identify"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Stage the photo and return the candidate species."""
        if (manager := _manager(request)) is None:
            return self.json_message(_t(request, "Not loaded"), HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            data = await _read_file(request, MAX_PHOTO_BYTES)
        except ValueError as err:
            return self.json_message(_t(request, str(err)), HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if data is None:
            return self.json_message(_t(request, "Missing file"), HTTPStatus.BAD_REQUEST)
        try:
            return self.json(await manager.async_identify(data))
        except ValueError as err:
            return self.json_message(_t(request, str(err)), HTTPStatus.UNSUPPORTED_MEDIA_TYPE)


class BackupView(HomeAssistantView):
    """Download a backup zip that was just created. Uses signed paths."""

    url = BACKUP_URL
    name = "api:plant_manager:backup"
    requires_auth = True

    async def get(self, request: web.Request, backup_id: str) -> web.StreamResponse:
        """Return the backup."""
        manager = _manager(request)
        path = manager.backup_path(backup_id) if manager else None
        if path is None or not await request.app[KEY_HASS].async_add_executor_job(
            os.path.isfile, path
        ):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.FileResponse(
            path,
            headers={
                "Content-Disposition": 'attachment; filename="plant-manager-backup.zip"',
                "Cache-Control": "no-store",
            },
        )


class UploadView(HomeAssistantView):
    """Import plants from CSV, or restore a backup (admins only)."""

    url = UPLOAD_URL
    name = "api:plant_manager:upload"
    requires_auth = True

    async def post(self, request: web.Request, kind: str) -> web.Response:
        """Handle the upload."""
        if (manager := _manager(request)) is None:
            return self.json_message(_t(request, "Not loaded"), HTTPStatus.SERVICE_UNAVAILABLE)
        if kind not in ("csv", "backup"):
            return self.json_message(_t(request, "Unknown upload"), HTTPStatus.NOT_FOUND)
        if kind == "backup" and not request["hass_user"].is_admin:
            return self.json_message(
                _t(request, "Only administrators can restore"), HTTPStatus.FORBIDDEN
            )
        try:
            data = await _read_file(request, MAX_UPLOAD_BYTES)
        except ValueError as err:
            return self.json_message(_t(request, str(err)), HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if data is None:
            return self.json_message(_t(request, "Missing file"), HTTPStatus.BAD_REQUEST)
        try:
            if kind == "csv":
                text = data.decode("utf-8-sig", errors="replace")
                return self.json(await manager.async_import_csv(text, _language(request)))
            return self.json(await manager.async_restore_backup(data))
        except ValueError as err:
            return self.json_message(_t(request, str(err)), HTTPStatus.BAD_REQUEST)
