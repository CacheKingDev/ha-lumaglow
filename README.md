![LumaGlow](https://raw.githubusercontent.com/CacheKingDev/ha-lumaglow/main/custom_components/lumaglow/brand/icon.png)

# LumaGlow für Home Assistant

Home-Assistant-Integration für die LumaGlow-Pixelmatrix (WS2812, z. B. 8×8 oder 16×16, ESP32/ESP8266) und den LumaGlow-LED-Strip (Firmware ab v0.11.0). Sie spricht die REST-API des Webinterfaces im lokalen Netz an. Ein MQTT-Broker oder Cloud-Dienst ist nicht nötig.

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
| GIF-Vorschau | Bild des laufenden GIFs (ein Frame in Matrixgröße, vergrößert; Größe ab Firmware v0.10.0 aus dem Gerät, sonst 16×16) |
| Playlist | Startet bzw. beendet die Playlist. Welche GIFs dabei sind, legst du im Webinterface fest (Attribut `gifs`). Ein einzelnes GIF auswählen beendet die Playlist. Ab Firmware v0.10.0 |
| Nächstes GIF | Springt in der laufenden Playlist zum nächsten GIF |
| Playlist zufällig | Konfiguration, gemischte statt Galerie-Reihenfolge |
| Playlist-Dauer pro GIF | Konfiguration, 10–3600 s |
| Strombegrenzung | Konfiguration, Obergrenze für den LED-Strom in mA (0 = keine Grenze, sonst 500–20000) |
| WLAN-Signal | Diagnose, dBm |
| Freier Speicher | Diagnose, freier Platz für GIFs |
| Letzter Neustart | Diagnose, Zeitpunkt des letzten Starts (aus der Laufzeit des Geräts) |
| LEDs | Diagnose, Datenpin, RGB/RGBW und Farbreihenfolge aus dem Einrichtungsassistenten, z. B. „GPIO4, RGB, GRB“. Ab Firmware v0.14.0 |

### LED-Strip

Ist das Gerät als LED-Strip eingerichtet (Firmware ab v0.11.0), gibt es keine GIF-Entitäten. Stattdessen:

| Entität | Funktion |
|---------|----------|
| Licht | An/aus, Helligkeit, Farbe (RGB), Weißton (1900–6500 K) und Effekt (Farbe, Atmen, Regenbogen, Feuer, Kerze, …). Eine Farbe bei einem Effekt ohne eigene Farbe (z. B. Regenbogen) schaltet auf „Farbe“ um |
| Effekt-Geschwindigkeit | 0–100 % |
| Effekt-Stärke | 0–100 %, je nach Effekt Dichte, Schweif, Funken, Flackern … |
| Palette | Farbverlauf, der sich auf den Effekt legt: Standard (Farben des Effekts), Farbe 1+2, Regenbogen, Party, Ozean, Wald, Lava, Wolken, Sonnenuntergang, Feuer, Polarlicht, Pastell, Eis, Herbst, Neon. Ab Firmware v0.12.0. Eine Farbe am Licht wählen stellt eine Palette mit eigenen Farben auf „Standard“ zurück, wie im Webinterface |

Die Effektliste kommt vom Gerät, neue Effekte einer neueren Firmware erscheinen also von selbst. Die zweite Farbe mancher Effekte (Wellen, Theater, Farbwischen, Auflösen) stellt nur das Webinterface ein.

Strom, Leistung, Strombegrenzung und Diagnose gibt es wie bei der Matrix. Wird das Gerät nach einem Werksreset von Matrix auf Strip umgestellt (oder umgekehrt), lädt die Integration den Eintrag selbst neu. Das gilt auch nach einem Firmware-Update, damit neue Effekte, Paletten und Entitäten erscheinen.

Der Zustand wird alle 10 s abgefragt. Die MAC-Adresse ist die eindeutige ID, mehrere Matrizen lassen sich also parallel einrichten. Ändert sich die IP, aktualisiert die Zeroconf-Erkennung den Eintrag. Antwortet unter dem Host ein anderes Gerät (andere MAC), wird die Matrix als nicht verfügbar angezeigt statt fremde Daten zu übernehmen.

Voraussetzung für mehrere Matrizen: Firmware ab v0.4.0. Ältere Versionen heißen alle `lumaglow.local` und überdecken sich gegenseitig.

## Beispiele

```yaml
action: light.turn_on
target:
  entity_id: light.lumaglow
data:
  brightness: 80
  effect: regenbogen.gif
```

Strip als warmes Nachtlicht:

```yaml
action: light.turn_on
target:
  entity_id: light.lumaglow
data:
  color_temp_kelvin: 2200
  brightness: 20
  effect: Farbe
```

Strip mit Feuer-Effekt in der Palette „Lava“ (Skript):

```yaml
sequence:
  - action: light.turn_on
    target:
      entity_id: light.lumaglow
    data:
      effect: Feuer
  - action: select.select_option
    target:
      entity_id: select.lumaglow_palette
    data:
      option: Lava
```

Wecklicht: um 6:30 der Sonnenaufgang. Die Dauer stellt die Effekt-Geschwindigkeit ein (0 % = 60 min, 50 % ≈ 30 min, 100 % = 1 min):

```yaml
triggers:
  - trigger: time
    at: "06:30:00"
actions:
  - action: light.turn_on
    target:
      entity_id: light.lumaglow
    data:
      effect: Sonnenaufgang
      brightness: 255
  - action: number.set_value
    target:
      entity_id: number.lumaglow_effekt_geschwindigkeit
    data:
      value: 50
```

Abends die Playlist starten:

```yaml
action: switch.turn_on
target:
  entity_id: switch.lumaglow_playlist
```
