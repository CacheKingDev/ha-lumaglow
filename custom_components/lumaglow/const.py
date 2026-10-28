"""Konstanten der LumaGlow-Integration."""

from datetime import timedelta

DOMAIN = "lumaglow"
MANUFACTURER = "LumaGlow"

# Abfrage-Intervall (/api/info + /api/gifs); der ESP8266 hat wenig RAM, also nicht zu oft
SCAN_INTERVAL = timedelta(seconds=10)
REQUEST_TIMEOUT = 10

# GIF-Auswahl (Licht-Effekt und Select), die das laufende GIF anhält (Matrix bleibt an, aber schwarz)
NO_GIF = "Kein GIF"
