# Änderungen

Alle Versionen von **N8-Hotspot** (DMR Die N8schicht), die neueste oben.
Die Nummern folgen [Semantic Versioning](https://semver.org/lang/de/): `MAJOR.MINOR.PATCH`.
Wie Versionen und Updates funktionieren, steht in [docs/de/updates.md](docs/de/updates.md).

## [1.1.0] – 2026-11-22

Updates direkt im Browser, frei einstellbare Farben und ein Link-Menü – N8-Hotspot bekommt damit denselben Adminbereich
wie das Dashboard von [HBlink4-FreeRadioID](https://github.com/dhartmann1979/HBlink4-FreeRadioID).

### ⬆️ Updates im Browser
- **Neuer Tab Admin → Updates.** Zeigt die installierte Version (Nummer und Commit), den Stand auf GitHub,
  die Änderungen der neuen Version aus dieser Datei und die Quelle des Updates.
- **Stündliche Prüfung:** N8-Hotspot fragt einmal pro Stunde bei GitHub nach (einstellbar 1–168 Stunden, abschaltbar).
  Es werden keine Daten über den Hotspot übertragen, nur die öffentliche Commit-Liste gelesen.
- **Hinweis für Admins:** Gibt es eine neue Version, steht oben ein blauer Balken „Version x.y.z is available“ mit **Show**.
- **Update now:** installiert genau die angezeigte Version. Zur Sicherheit wird das eigene Passwort noch einmal abgefragt
  (mit derselben Sperre nach Fehlversuchen wie beim Login). Danach läuft alles von selbst:
  1. `git fetch` + Fast-Forward auf den gezeigten Commit (nie ein fremder Server, keine Git-Hooks, keine lokalen Änderungen überschrieben)
  2. Python-Pakete neu, wenn sich `requirements.txt` geändert hat
  3. `MMDVM-Host.ini` und `DMRGateway.ini` neu schreiben, **MMDVMHost und DMRGateway neu starten** (abschaltbar)
  4. **Weboberfläche neu starten** – die Seite lädt sich danach von selbst neu
- **Automatische Updates (optional):** auf Wunsch installiert der Hotspot neue Versionen selbst, in einer frei wählbaren
  Stunde (Vorgabe 04:00) und nur, wenn gerade niemand sendet und keine Kalibrierung läuft.
- Die Dienste werden über die bestehende sudo-Regel aus `install.sh` neu gestartet; es ist **keine Änderung an `/etc/sudoers`** nötig.
- Jedes Update steht im Protokoll (*Sessions & log*) mit Benutzer und Commit-Bereich.

### 🎨 Aussehen (N8 Theme)
- **Neuer Tab Admin → Appearance** mit derselben Farb-Engine wie HBlink4-FreeRadioID und der FRN-Weboberfläche.
- **7 Farbprofile:** N8 Night (Vorgabe), Ocean, Aurora, Ember, Violet, Graphite und das helle **Daylight**.
- **Jede Farbe frei wählbar:** Akzent, Akzent 2, Hintergrund, drei Leuchtfarben, Text und Kartentönung.
  Dazu Regler für Hintergrund-Leuchten, Kartenhelligkeit, Rundung und Glas-Unschärfe.
- **Live-Vorschau** mit Kontrollanzeige: warnt, wenn Text auf dem Hintergrund schlecht lesbar ist (Kontrast < 4,5 : 1).
- **Export / Import:** Farbschema als JSON kopieren und in einem anderen N8-Dashboard einfügen – sieht überall gleich aus.
- Heller Modus für alle Bereiche (Live, Statistik, Talkgroups, Admin, Dialoge).

### 🔗 Link-Menü
- **Neuer Tab Admin → Links:** eigene Links (Name, Adresse, Emoji, neuer Tab) für ein Menü oben rechts, für alle Besucher sichtbar.
- **Site-Icons:** Der Hotspot holt das Favicon der verlinkten Seite einmal, speichert es in seiner SQLite-Datenbank
  und zeigt es im Menü. Ohne Internet bleibt das Emoji stehen. Nur öffentliche Adressen werden abgefragt (Schutz gegen SSRF),
  SVG-Icons werden auf Skripte geprüft.
- Ab Werk: DMR Die N8schicht und FreeRadioID.net.

### 📱 Darstellung
- **Kopfzeile am Handy kompakter:** Live-Daten und Modem sind zwei Statuspunkte, Links und Benutzer nur noch Symbole.
- **Admin-Tabs am Handy** in einer wischbaren Zeile, der aktive Tab rückt automatisch ins Bild.
- **Neue Fußzeile** mit © Die N8schicht, Version, Commit und Datum.

### Technik
- Neue Module `n8hotspot/updater.py`, `n8hotspot/uiconfig.py`, `n8hotspot/n8theme.py`, `n8hotspot/siteicons.py`.
- Neue API: `GET /api/admin/update`, `POST /api/admin/update/install`, `GET/POST /api/admin/ui…`, `GET /api/link-icon/{key}`;
  `/api/info` liefert zusätzlich `theme`, `links` und `build`.
- Version steht in der Datei `VERSION`; GitHub erzeugt Tag und Release automatisch aus dieser Datei (`.github/workflows/release.yml`).
- 6 neue Tests (Links, Update-Einstellungen, Passwortabfrage, Icon-Cache, Theme), insgesamt 27.

## [1.0.0] – 2026-11-19

Erste Ausgabe von N8-Hotspot: MMDVMHost- und DMRGateway-Weboberfläche im Design von DMR Die N8schicht.

- Live-Ansicht mit ON AIR, Zeitschlitzen, Hotspot-Daten und Last Heard (RF und Netz, BER, RSSI)
- Statistik (heute, 24 h, 7 und 30 Tage), Talkgroup-Verzeichnis mit der N8schicht-Liste
- FreeRadioID.net: Avatare, FRID-Kennzeichen, Profile und DMR-ID-Datenbank
- Kalibrierung mit MMDVMCal im Browser, Modem-Suche für alle seriellen Schnittstellen
- Adminbereich: Einstellungen, Benutzer (Admin/Viewer), System und Dienste, Logs, Konfigurationsdateien, Sitzungen und Protokoll
- Geführte Einrichtung (`setup.sh`), Installation ohne Fragen (`install.sh`) und eigenes DietPi-Image (`build-image.sh`)
