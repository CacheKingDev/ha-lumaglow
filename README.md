![LumaGlow](https://raw.githubusercontent.com/CacheKingDev/ha-lumaglow/main/custom_components/lumaglow/brand/icon.png)

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
| LED-Strom | geschätzter Strom der LEDs in mA, Mittel der letzten 10 s (Firmware ab v0.8.0; ältere: Wert des letzten Bildes) |
| LED-Leistung | LED-Strom × 5 V in W. Für das Energie-Dashboard mit dem Helfer „Integral“ (Riemann-Summe) in kWh umrechnen |
| GIF | Auswahl des laufenden GIFs, wie der Licht-Effekt („Kein GIF“ hält das GIF an) |
| GIF-Vorschau | Bild des laufenden GIFs (ein Frame, 16×16 Pixel vergrößert) |
| Strombegrenzung | Konfiguration, Obergrenze für den LED-Strom in mA (0 = keine Grenze, sonst 500–20000) |
| WLAN-Signal | Diagnose, dBm |
| Freier Speicher | Diagnose, freier Platz für GIFs |
| Letzter Neustart | Diagnose, Zeitpunkt des letzten Starts (aus der Laufzeit des Geräts) |

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
