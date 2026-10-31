"""Plant photos as a media source.

AI Task takes attachments as media source ids that resolve to a local file, so
this is how a photo reaches the AI for identification. It also makes plant
photos browsable in the media panel.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NAME, PHOTO_URL, STAGED_URL
from .db import NotFoundError
from .manager import get_manager, mime_type


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up the plant photo media source."""
    return PlantPhotoMediaSource(hass)


class PlantPhotoMediaSource(MediaSource):
    """Photos stored by Plant Manager: ``photo/<photo id>`` and ``staged/<staged id>``."""

    name = NAME

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a photo to its file."""
        if (manager := get_manager(self.hass)) is None:
            raise Unresolvable("Plant Manager is not loaded")
        kind, _, key = item.identifier.partition("/")
        path: str | None = None
        url = ""
        if kind == "photo":
            try:
                path = await manager.async_photo_file(key)
            except NotFoundError:
                path = None
            url = PHOTO_URL.format(photo_id=key)
        elif kind == "staged":
            path = manager.staged_path(key)
            url = STAGED_URL.format(staged_id=key)
        if path is None:
            raise Unresolvable(f"Unknown photo {item.identifier}")
        return PlayMedia(url, mime_type(path), path=Path(path))

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """List the cover photo of every plant."""
        manager = get_manager(self.hass)
        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"photo/{photo['id']}",
                media_class=MediaClass.IMAGE,
                media_content_type="image/jpeg",
                title=plant["name"],
                can_play=True,
                can_expand=False,
            )
            for plant in (manager.plants if manager else [])
            for photo in plant["photos"][:1]
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.IMAGE,
            title=NAME,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.IMAGE,
            children=children,
        )
