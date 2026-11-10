"""Vorschaubild des laufenden GIFs (ein Bild aus /api/gifs/thumb, vergrößert als PNG)."""

from __future__ import annotations

import logging
import struct
import zlib

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import LumaGlowError
from .coordinator import LumaGlowConfigEntry, LumaGlowCoordinator
from .entity import LumaGlowEntity

_LOGGER = logging.getLogger(__name__)

TARGET_SIDE = 256   # längere Seite des PNGs in Pixeln; ohne Vergrößerung zeigt der Browser es verschwommen an


def _matrix_size(info: dict) -> tuple[int, int]:
    """Matrixgröße aus /api/info (Firmware ab v0.10.0), ältere Firmware: 16x16."""
    return int(info.get("width", 16)), int(info.get("height", 16))


def _rgb_to_png(rgb: bytes, width: int, height: int) -> bytes:
    """RGB-Pixel (zeilenweise von oben links) als PNG, jedes Pixel scale x scale groß."""
    scale = max(1, TARGET_SIDE // max(width, height))
    row_bytes = width * 3
    rows = []
    for y in range(height):
        row = rgb[y * row_bytes:(y + 1) * row_bytes]
        scaled = b"".join(row[x * 3:x * 3 + 3] * scale for x in range(width))
        rows.append((b"\x00" + scaled) * scale)   # Filter 0 = keiner

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)   # 8 Bit, RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LumaGlowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LumaGlowGIFImage(entry.runtime_data)])


class LumaGlowGIFImage(LumaGlowEntity, ImageEntity):
    _attr_translation_key = "gif_preview"
    _attr_content_type = "image/png"

    def __init__(self, coordinator: LumaGlowCoordinator) -> None:
        super().__init__(coordinator, "gif_preview")
        ImageEntity.__init__(self, coordinator.hass)
        self._gif = coordinator.data.current_gif
        self._png: bytes | None = None
        self._attr_image_last_updated = dt_util.utcnow()

    @callback
    def _handle_coordinator_update(self) -> None:
        gif = self.coordinator.data.current_gif
        if gif != self._gif:
            # Neues Bild erst laden, wenn das Frontend es anfragt
            self._gif = gif
            self._png = None
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        gif = self._gif
        if gif is None:
            return None
        if self._png is None:
            try:
                rgb = await self.coordinator.client.get_thumb(gif)
            except LumaGlowError as err:
                _LOGGER.debug("Vorschau für %s nicht geladen: %s", gif, err)
                return None
            width, height = _matrix_size(self.coordinator.data.info)
            if len(rgb) != width * height * 3:
                _LOGGER.debug("Vorschau für %s hat %d Bytes statt %d", gif, len(rgb), width * height * 3)
                return None
            png = _rgb_to_png(rgb, width, height)
            # Während des Ladens kann ein anderes GIF gestartet sein
            if gif != self._gif:
                return png
            self._png = png
        return self._png
