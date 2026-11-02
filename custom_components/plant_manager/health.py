"""Explicit photo checks via the existing Pl@ntNet free account.

No background analysis, paid provider or key exposed to the frontend. Extra
tables are inside the existing SQLite database and therefore in its backups.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import math
import uuid

import aiohttp
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PLANTNET_API_KEY, MAX_PHOTO_BYTES, PLANTNET_API
from .db import NotFoundError
from .http import _language, _read_file, _t
from .i18n import tr
from .manager import get_manager, image_extension

TIMEOUT = aiohttp.ClientTimeout(total=45)
MAX_CANDIDATES = 5
MAX_LABEL_LENGTH = 600
HISTORY_LIMIT = 20
NOTE_CANDIDATES = 3
LOCK_KEY = "plant_manager_health_lock"


class CheckError(Exception):
    """Only fixed, non-secret messages leave this module."""


def free_quota(subscription: dict, daily: dict) -> dict:
    """Fail closed if the account cannot be established as a free account.

    The limit itself comes from the account's own quota, not from this code.
    """
    contract = subscription.get("contract") or {}
    if not isinstance(contract, dict):
        contract = {}
    plan = contract.get("plan") or subscription.get("plan")
    # Free accounts cannot access the contract endpoint (403); an explicit paid plan is rejected.
    restricted = plan is None and subscription.get("contract_restricted") is True
    if str(plan).lower() != "free" and not restricted:
        raise CheckError(
            "The free Pl@ntNet plan could not be confirmed. No photo was sent."
        )
    quota = daily.get("quota")
    identify = quota.get("identify") if isinstance(quota, dict) else None
    if not isinstance(identify, dict):
        identify = {}
    remaining, total = identify.get("remaining"), identify.get("total")
    if type(remaining) is not int or type(total) is not int or total <= 0:
        raise CheckError("The free daily quota could not be confirmed. No photo was sent.")
    if remaining < 1:
        raise CheckError("The free daily quota is used up. Please try again tomorrow.")
    return {"remaining": remaining, "total": total, "plan": "free"}


def candidates_from(payload: dict) -> list[dict]:
    """Keep only bounded, renderable suggestions, never a healthy verdict."""
    out = []
    rows = payload.get("results", [])
    if not isinstance(rows, list):
        raise CheckError("Pl@ntNet did not return a usable list of results.")
    for row in rows[:MAX_CANDIDATES]:
        if not isinstance(row, dict):
            continue
        try:
            score = float(row.get("score", 0))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score) or not 0 <= score <= 1:
            continue
        code = str(row.get("name") or "")[:40]
        label = str(row.get("description") or row.get("label") or code)[:MAX_LABEL_LENGTH]
        if code and label:
            out.append({"code": code, "label": label, "score": score})
    return sorted(out, key=lambda r: r["score"], reverse=True)


async def _api(session, key: str, route: str, data=None, lang: str = "en") -> dict:
    """Do not propagate aiohttp exceptions: their URLs contain the API key."""
    params = {"api-key": key}
    if data is not None:
        params.update(
            {"lang": lang, "nb-results": str(MAX_CANDIDATES), "include-related-images": "false"}
        )
    method = session.post if data is not None else session.get
    try:
        async with method(
            PLANTNET_API + route, params=params, data=data, timeout=TIMEOUT
        ) as resp:
            if resp.status == 403 and route == "/subscription":
                return {"contract_restricted": True}
            if resp.status in (401, 403):
                raise CheckError("Pl@ntNet rejected the existing access.")
            if resp.status == 429:
                raise CheckError("The free daily quota is used up. Please try again tomorrow.")
            if resp.status == 404 and data is not None:
                return {"results": []}
            if resp.status >= 400:
                raise CheckError("Pl@ntNet could not process the request. Please try again later.")
            value = await resp.json()
            if not isinstance(value, dict):
                raise CheckError("Pl@ntNet returned an unexpected response.")
            return value
    except (aiohttp.ClientError, TimeoutError, ValueError):
        raise CheckError(
            "Pl@ntNet is not reachable right now or did not return a readable response."
        ) from None


def _history(manager, plant_id: str) -> list[dict]:
    db = manager.db
    with db._lock:
        with db.conn:
            db.conn.execute(
                """CREATE TABLE IF NOT EXISTS garden_health_checks (
                id TEXT PRIMARY KEY, plant_id TEXT NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
                checked_at TEXT NOT NULL, result TEXT NOT NULL)"""
            )
        return [
            json.loads(row[0])
            for row in db.conn.execute(
                "SELECT result FROM garden_health_checks WHERE plant_id=? "
                "ORDER BY checked_at DESC LIMIT ?",
                (plant_id, HISTORY_LIMIT),
            )
        ]


def _save(manager, plant_id: str, record: dict) -> None:
    with manager.db._lock, manager.db.conn:
        manager.db.conn.execute(
            "INSERT INTO garden_health_checks VALUES (?,?,?,?)",
            (
                record["id"],
                plant_id,
                record["checked_at"],
                json.dumps(record, ensure_ascii=False),
            ),
        )


class HealthView(HomeAssistantView):
    """A plant's photo checks, and running a new one."""

    url = "/api/plant_manager/health/{plant_id}"
    name = "api:plant_manager:health"
    requires_auth = True

    async def _context(self, request, plant_id):
        manager = get_manager(request.app[KEY_HASS])
        if manager is None:
            raise CheckError("The plant manager has not loaded yet.")
        plant = await manager._run(manager.db.get_plant, plant_id)
        return manager, plant

    async def _quota(self, request, manager):
        key = manager.options.get(CONF_PLANTNET_API_KEY)
        if not key:
            raise CheckError("The free photo check needs Pl@ntNet access.")
        session = async_get_clientsession(request.app[KEY_HASS])
        sub = await _api(session, key, "/subscription")
        daily = await _api(session, key, "/quota/daily")
        return session, key, free_quota(sub, daily)

    async def get(self, request, plant_id):
        """History and a free-plan preflight; no image inference on GET."""
        try:
            manager, _plant = await self._context(request, plant_id)
            checks = await manager._run(_history, manager, plant_id)
            result = {"checks": checks, "ready": False}
            try:
                _, _, quota = await self._quota(request, manager)
                result.update(ready=True, quota=quota)
            except CheckError as err:
                result["message"] = _t(request, str(err))
            return self.json(result)
        except NotFoundError:
            return self.json_message(_t(request, "The plant was not found."), 404)
        except CheckError as err:
            return self.json_message(_t(request, str(err)), 503)

    async def post(self, request, plant_id):
        """Check one photo, and keep the result with the plant."""
        hass = request.app[KEY_HASS]
        lock = hass.data.setdefault(LOCK_KEY, asyncio.Lock())
        if lock.locked():
            return self.json_message(
                _t(request, "A photo check is already running. Please wait a moment."), 429
            )
        try:
            async with lock:
                manager, plant = await self._context(request, plant_id)
                lang = _language(request)
                data = await _read_file(request, MAX_PHOTO_BYTES)
                if not data:
                    return self.json_message(_t(request, "Please choose a current photo."), 400)
                extension = image_extension(data)
                if extension not in ("jpg", "jpeg", "png"):
                    return self.json_message(_t(request, "Please use a JPEG or PNG photo."), 415)
                # This must precede the only inference call, every time.
                session, key, quota = await self._quota(request, manager)
                await manager._run(_history, manager, plant_id)
                form = aiohttp.FormData()
                form.add_field(
                    "images",
                    data,
                    filename="plant." + extension,
                    content_type="image/png" if extension == "png" else "image/jpeg",
                )
                form.add_field("organs", "auto")
                payload = await _api(
                    session, key, "/diseases/identify", form, lang
                )
                candidates = candidates_from(payload)
                photo = await manager.async_add_photo(plant_id, data, "health-check")
                record = {
                    "id": uuid.uuid4().hex,
                    "checked_at": datetime.now(UTC).isoformat(),
                    "provider": "Pl@ntNet",
                    "species": plant.get("species"),
                    "photo_id": photo["id"],
                    "candidates": candidates,
                    "remaining": payload.get(
                        "remainingIdentificationRequests", max(0, quota["remaining"] - 1)
                    ),
                }
                await manager._run(_save, manager, plant_id, record)
                if candidates:
                    labels = "; ".join(c["label"] for c in candidates[:NOTE_CANDIDATES])
                    note = tr(
                        lang,
                        "Photo check (Pl@ntNet), not a diagnosis. Possible causes: {labels}",
                        labels=labels,
                    )
                else:
                    note = tr(
                        lang,
                        "Photo check (Pl@ntNet), not a diagnosis. No usable match. "
                        "This does not confirm that the plant is healthy.",
                    )
                await manager.async_log(plant_id, "note", notes=note, source="health-check")
                return self.json(record)
        except NotFoundError:
            return self.json_message(_t(request, "The plant was not found."), 404)
        except CheckError as err:
            return self.json_message(_t(request, str(err)), 400)
        except ValueError:
            return self.json_message(
                _t(request, "The photo is too large or its format is not supported."), 413
            )
