"""Konstanten der LumaGlow-Integration."""

from datetime import timedelta

DOMAIN = "lumaglow"
MANUFACTURER = "LumaGlow"

# Abfrage-Intervall (/api/info + /api/gifs); der ESP8266 hat wenig RAM, also nicht zu oft
SCAN_INTERVAL = timedelta(seconds=10)
REQUEST_TIMEOUT = 10
