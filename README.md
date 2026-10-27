<!-- Absolute URLs: HACS zeigt relative Bildpfade nicht an. Ohne <picture>-Unterstützung erscheint das Icon (lesbar auf hellem und dunklem Hintergrund). -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/CacheKingDev/ha-lumaglow/main/custom_components/lumaglow/brand/dark_logo@2x.png">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/CacheKingDev/ha-lumaglow/main/custom_components/lumaglow/brand/logo@2x.png">
  <img alt="LumaGlow" src="https://raw.githubusercontent.com/CacheKingDev/ha-lumaglow/main/custom_components/lumaglow/brand/icon@2x.png" height="128">
</picture>

# LumaGlow für Home Assistant

Home-Assistant-Integration für die LumaGlow-Pixelmatrix (16×16 WS2812, ESP32/ESP8266). Sie spricht die REST-API des Webinterfaces im lokalen Netz an. Ein MQTT-Broker oder Cloud-Dienst ist nicht nötig.

## Installation über HACS

1. HACS → Menü (⋮) → **Benutzerdefinierte Repositories**.
2. URL `https://github.com/CacheKingDev/ha-lumaglow` eintragen, Typ **Integration**.
3. **LumaGlow** suchen, herunterladen, Home Assistant neu starten.

Manuell: Ordner `custom_components/lumaglow` nach `<HA-Konfiguration>/custom_components/` kopieren und neu starten.

## Einrichtung

Die Matrix wird per Zeroconf (`_lumaglow._tcp`) automatisch erkannt und erscheint unter *Einstellungen → Geräte & Dienste*. Sonst: *Integration hinzufügen → LumaGlow* und Host eingeben (z. B. `lumaglow-563308.local` oder die IP).

Voraussetzung: Firmware mit mDNS-Dienst `_lumaglow._tcp` (für die automatische Erkennung) und Gerät im Heim-WLAN.

## Entitäten

| Entität | Funktion |
|---------|----------|
| Licht | An/aus, Helligkeit, Effekt = GIF auswählen („Kein GIF“ hält das GIF an) |
| WLAN-Signal | Diagnose, dBm |
| Freier Speicher | Diagnose, freier Platz für GIFs |

Der Zustand wird alle 10 s abgefragt. Die MAC-Adresse ist die eindeutige ID, mehrere Matrizen lassen sich also parallel einrichten. Ändert sich die IP, aktualisiert die Zeroconf-Erkennung den Eintrag. Antwortet unter dem Host ein anderes Gerät (andere MAC), wird die Matrix als nicht verfügbar angezeigt statt fremde Daten zu übernehmen.

Voraussetzung für mehrere Matrizen: Firmware ab v0.4.0. Ältere Versionen heißen alle `lumaglow.local` und überdecken sich gegenseitig.

## Beispiel

```yaml
action: light.turn_on
target:
  entity_id: light.lumaglow
data:
  brightness: 80
  effect: regenbogen.gif
```
