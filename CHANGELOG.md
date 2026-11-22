# Änderungen

Alle Versionen von **N8-Hotspot** (DMR Die N8schicht), die neueste oben.
Die Nummern folgen [Semantic Versioning](https://semver.org/lang/de/): `MAJOR.MINOR.PATCH`.
Wie Versionen und Updates funktionieren, steht in [docs/de/updates.md](docs/de/updates.md).

## [1.2.0] – 2026-11-22

Der Modem-Scan funktioniert wieder zuverlässig, und N8-Hotspot prüft und repariert jetzt seine Berechtigungen – bei jedem Update.

### 🔍 Modem-Scan
- **Stop MMDVMHost & scan:** Hält MMDVMHost eine Schnittstelle offen, wurde sie bisher nur „in use“ gemeldet – hing MMDVMHost am
  falschen Port, fand der Scan das Modem nie. Jetzt hält ein Knopf MMDVMHost für ein paar Sekunden an, fragt alle Schnittstellen
  direkt und startet MMDVMHost danach wieder (nicht während einer Kalibrierung; steht im Protokoll).
- Darf die Weboberfläche eine Schnittstelle nicht öffnen, zeigt der Scan oben den Grund und den Befehl zum Reparieren.
- **Warum der Scan scheitern konnte:** (1) MMDVMHost hält die Modem-Schnittstelle offen – der Scan fasst sie nicht an, und hängt
  MMDVMHost am falschen Port, meldet niemand ein Modem; (2) der Weboberfläche fehlt die Gruppe `dialout` (ältere Installation, Gruppe
  nachträglich gesetzt, Dienst nicht neu gestartet) – dann ist jede Schnittstelle *no permission*; (3) eine Login-Konsole belegt den UART.
  Für (1) gibt es den neuen Knopf, (2) und (3) prüft und repariert die neue Berechtigungsprüfung. `n8hotspot.service` hat die
  Gruppe jetzt zusätzlich fest eingetragen (`SupplementaryGroups=dialout`, wie MMDVMHost).

### 🔐 Berechtigungen
- Neue Kachel **Admin → Updates → 🔐 Permissions** (auch `GET /api/admin/permissions`): Gruppe `dialout`, Zugriff auf jede
  Modem-Schnittstelle, Linux-Konsole auf dem UART, Bluetooth/Mini-UART am Pi, sudo-Regel für Neustarts, Schreibrechte für
  Programmordner und Python-Umgebung – jeweils mit Grund und Lösung.
- Neues Skript **`scripts/permissions.sh`** (root): prüft (`--check`) und repariert Gruppen, systemd-Dienste (Port bleibt erhalten),
  sudo-Regel, Besitzer des Programmordners, Login-Konsole auf der Modem-Schnittstelle und die Kernel-Konsole am Pi.
- **`scripts/update.sh` ruft es bei jedem Update auf**, `install.sh` ebenso. Nach einem Update im Browser wird die Prüfung
  angezeigt; ändern sich Dienst-Dateien oder fehlt etwas, nennt der Update-Dialog den einmaligen Befehl.
- `update.sh` ist gegen das Ersetzen während des Laufs geschützt (bash liest das Skript jetzt vollständig vor dem `git pull`).

### Doku
- Adminbereich (Modem-Scan), Updates (neuer Abschnitt *Berechtigungen*), Fehlersuche, Technik (API); neue Screenshots.

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
