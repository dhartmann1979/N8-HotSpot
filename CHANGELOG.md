# Änderungen

Alle Versionen von **N8-Hotspot** (DMR Die N8schicht), die neueste oben.
Die Nummern folgen [Semantic Versioning](https://semver.org/lang/de/): `MAJOR.MINOR.PATCH`.
Wie Versionen und Updates funktionieren, steht in [docs/de/updates.md](docs/de/updates.md).

## [1.5.0] – 2026-11-25

**Der Hotspot sieht aus wie ein Funkgerät – und aktualisiert sich wie die anderen N8schicht-Projekte.**

> **Einmalig nach dem Update von 1.4.x:** `sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms` – richtet die neuen sudo-Regeln und
> „Update jetzt“ ein (das erste Update läuft noch über den alten Weg). Danach geht alles im Browser.

### 📻 Live-Ansicht als digitales Funkgerät
- Die Zeitschlitze bilden **einen Block wie ein Funkgerät**: Gehäuse mit **LED-Leiste** und einem **Display** mit beiden Zeitschlitzen.
- **LEDs:** **RX** (grün, pulsiert – ein Funkgerät sendet in den Hotspot), **TX** (rot – der Hotspot sendet, Gespräch aus dem Netz),
  **Modus** (DMR blau, IDLE grau, LOCKOUT gelb blinkend, ERROR/STOPPED rot), **NET** (Anmeldung am DMR-Server) und **MODEM**.
- **Display:** Kopfzeile mit Rufzeichen, Frequenz (bei Duplex RX/TX), Color Code, DMR-Server mit Verbindungsstatus und Uhrzeit;
  je Zeitschlitz eine Zeile mit **▼ RX / ▲ TX**, Avatar, Rufzeichen und FRID, Name und Ort, Talkgroup mit Namen, laufender
  Sprechzeit sowie bei Funk einem **S-Meter** (RSSI, ab S9 gelb) und einem **BER-Balken** (grün < 1 %, gelb bis 3 %, rot darüber).
  Beim Simplex-Hotspot steht TS1 abgedunkelt als *nicht genutzt*. Fußzeile mit Hotspot-ID, Simplex/Duplex, Modem, Standort.
- **Heute** (Gespräche, Sprechzeit, Funk, Netz, Funk-BER) sitzt schlank im Gehäuse; die eigene Karte *Hotspot* entfällt – alles steht im Display.
- Achtung, Farben gedreht: Funk-Durchgänge sind jetzt **grün (RX)**, Netz-Durchgänge **rot (TX)** – aus Sicht des Hotspots wie bei einem Funkgerät.

### 🎚️ Vocoder & Signal (neu)
- **BER live:** die Bitfehlerrate des laufenden Funk-Durchgangs zweimal pro Sekunde als Kurve mit den Bereichen sauber / hörbar / schlecht;
  nach dem Durchgang bleibt sie bis zum nächsten stehen.
- **Letzte Durchgänge:** Balken für die letzten 40 – BER (Funk, farbig) und Paketverlust (Netz, blau), mit Zeit und Rufzeichen beim Überfahren.
- **RSSI (Funk):** Verlauf der Empfangsstärke mit Mittelwert.
- **Sprachqualität heute:** Anteil sauberer/hörbarer/schlechter Funk-Durchgänge, Ø und max. BER, Ø Paketverlust, **AMBE+2-Sprachrahmen**
  über Funk und Netz (50 je Sekunde) und die geschätzt im Netz verlorenen.
- Neue Schnittstelle `GET /api/signal` (Sichtbereich): heute, je Stunde, letzte 40 Durchgänge.
- **Last Heard schlanker:** eine Zeile je Gespräch, Quelle als 📻/🌐 am Rufzeichen, erst 12 Zeilen, **Mehr anzeigen** bis 40.
- Demo: realistischere BER/RSSI (auch schwache Signale), der erste Durchgang nach dem Start kommt über Funk.

### 🧩 Dienste, Berechtigungen & „Update jetzt“ – das N8 Admin-Kit
Derselbe Baustein wie im HobbyRadioPortal, adn-frn-server und HBlink4-FreeRadioID (nach dem Vorbild von N8 Crosslink):
`scripts/n8-admin.sh` (root-Helfer, identisch in allen Repos) + `scripts/n8-admin.conf` (Hotspot-Daten) + `n8hotspot/n8_admin.py`.
- **Admin → System → 🧩 Dienste:** MMDVMHost, DMRGateway, MQTT, Weboberfläche und Update-Auslöser mit Zustand, **Autostart**-Schalter,
  **Neu starten · Starten · Stoppen** (die Weboberfläche nur neu starten).
- **Admin → System → 🔐 Berechtigungen & sudo:** prüfen und **Korrigieren** auf Knopfdruck (prüfen → korrigieren → erneut prüfen) –
  Dienst-Benutzer und Gruppen, Programm root und schreibgeschützt, Daten und Passwörter (Datenbank, ini-Dateien 600), Units,
  „Update jetzt“, sudo (installiert, eingebunden, gültig, aktuell, wirksam) und die **Modem-Schnittstelle** (Zugriff, Linux-/Login-Konsole,
  Bluetooth-UART; über die neuen Kit-Hooks `n8_check_extra`/`n8_fix_extra`).
- **Update jetzt** schreibt nur `data/update.request`; `n8hotspot-update.path` startet das Update **als root**: nur vorspulen (Abbruch bei
  von Hand geänderten Dateien), Pakete, Dienste aus den Vorlagen, ini-Dateien, Rechte und sudo, Neustart, **Prüfung 90 s**, sonst
  **automatisch zurück**. **📜 Update-Protokoll** unter *Admin → Updates*. Automatische Updates nachts laufen genauso.
- **Programmordner gehört jetzt root** (für den Dienst schreibgeschützt), nur `data/` gehört `n8hotspot`.
- sudo: `/etc/sudoers.d/n8hotspot-n8admin` mit exakten Befehlen; die alte `/etc/sudoers.d/n8hotspot` entfernt das erste Update.
- Entfernt: N8 update guard (`n8_update_guard.py`, `n8-update-guard.sh`, `ExecStartPre` in der Unit). `scripts/permissions.sh` und
  `scripts/update.sh` rufen jetzt `n8-admin.sh` auf; `install.sh` richtet alles mit `fix-perms` ein.
- Neue API: `GET /api/admin/services`, `POST /api/admin/services/{unit}/{action}`, `GET /api/admin/perms`, `POST /api/admin/perms/fix`,
  `GET /api/admin/update-log`. `GET /api/admin/permissions` prüft nur noch den Modem-Zugriff der laufenden Weboberfläche.

### 📚 Doku
- [Live & Statistik](docs/de/bedienung.md): *Das Funkgerät* (LEDs, Display), *Vocoder & Signal*, Last Heard; [Updates](docs/de/updates.md):
  Update jetzt über das Kit, *Dienste, Berechtigungen & sudo*, sudo-Befehle; [Technik](docs/de/technik.md) (API, sudo), [Sicherheit](docs/de/sicherheit.md),
  [Fehlersuche](docs/de/fehlersuche.md), [Adminbereich](docs/de/adminbereich.md), [Installation](docs/de/installation.md), README.
- Screenshots neu: `live.png`, `live-mobile.png`, `radio.png`, `signal.png`, `admin-system.png`, `admin-updates.png`; `on-air.png` und `permissions.png` entfernt.

### 🧪 Tests
- 38 Tests grün, neu: Kit-Endpunkte (Dienste, Rechte, Update-Protokoll), Signal-Statistik, Funkgerät-Ansicht, Kit identisch in allen Repos.

## [1.4.2] – 2026-11-24

### 🎨 Eine Designsprache mit dem HobbyRadioPortal
Der N8 Hotspot bleibt **eigenständig** (eigenes Image, eigene Weboberfläche, kein Plugin im Portal), spricht aber jetzt
dieselbe Designsprache wie das neue [HobbyRadioPortal](https://github.com/dhartmann1979/HobbyRadioPortal):
- **N8 Look 1.0** (`static/n8-look.css`) – dieselbe Datei wie im Portal (`portal/static/vendor/n8-look.css`). Sie liegt über N8 Theme 2 und gleicht die Feinheiten an:
  - der Hintergrund des Themes läuft über die ganze Seitenlänge (vorher endete der Farbverlauf nach einer Bildschirmhöhe),
  - die Kennzahl-Kacheln unter **Heute** leuchten unten rechts in eigener Farbe (Gespräche blau, Sprechzeit grün, Funk orange, Netz violett, BER rot) wie die Kacheln im Portal,
  - Abschnittsüberschriften klein, gesperrt und in Großbuchstaben wie im Portal,
  - die **Fußzeile** ist eine Glaskarte mit dem N8-Icon.
- Im Portal erscheint der Hotspot (abschaltbar) nur als Verweis mit Erreichbarkeitsprüfung – siehe Plugin `hotspot` im Portal.
- Doku: Screenshot **Live** neu, neuer Screenshot der Fußzeile (`docs/images/footer.png`), Abschnitt „Aussehen“ in der Bedienung ergänzt.

## [1.4.1] – 2026-11-24

### 🌐 N8 Kit 1.0.1
- Absätze, die im Quelltext über mehrere Zeilen gehen, werden beim Umschalten **DE | EN** als Ganzes übersetzt (vorher Zeile für Zeile,
  deshalb blieben längere Hilfetexte manchmal in der Originalsprache). `n8-kit.js` ist wieder in allen vier N8schicht-Projekten gleich
  (HBlink4-FreeRadioID 1.6.0, adn-frn-server, N8-HotSpot, N8 Crosslink).

## [1.4.0] – 2026-11-24

Sprache **DE | EN**, Updates mit Fortschritt und Rollback und strengere Sicherheits-Header – mit dem **N8 Kit**, das jetzt in N8-HotSpot,
HBlink4-FreeRadioID, adn-frn-server und N8 Crosslink gleich ist. Ausführlich: [docs/de/sicherheit.md](docs/de/sicherheit.md).

### 🌐 Sprache DE | EN
- Umschalter **DE | EN** in der Kopfzeile zwischen 🔗 Links und Anmeldung, **Standard Deutsch**. Umschalten ohne Neuladen; die Wahl gilt
  per Cookie (`n8_lang`) für alle N8schicht-Oberflächen auf dem Gerät. `?lang=en` für Links.
- Deutsche Texte für Kopfzeile, Statusleiste, Live, Statistik, Talkgroups und den ganzen Adminbereich (Settings mit Modem, DMR-Betrieb,
  Server, ID-Liste, FreeRadioID, Experte; Kalibrierung; Benutzer; Aussehen; Links; System; Updates mit Berechtigungen; Protokolle;
  Konfigurationsdateien; Sitzungen) in `static/i18n-app.js`.

### ⬆️ Updates wie in N8 Crosslink
- **Hinweis** unter der Statusleiste im N8-Kit-Stil: *Update verfügbar: alt → neu* mit **Was ist neu?**, **Jetzt aktualisieren**,
  **Details**, **Später** (einen Tag). Ersetzt den blauen Balken mit *Show*.
- **Admin → Updates → ⬆️ Updates**: gleiche Kachel wie in den anderen Projekten (installiert, GitHub, zuletzt geprüft, automatische Prüfung,
  letztes Update, Quelle, Neuerungen). Die Update-Einstellungen und die Berechtigungen bleiben daneben.
- **Fortschritt:** Fenster mit Neuerungen, Ablauf und Passwortabfrage, danach *geladen und eingespielt → Dienst startet neu →
  Weboberfläche wird geprüft*; ein falsches Passwort lässt das Fenster offen. Fehlgeschlagene Teilschritte erscheinen als Hinweis.
- **Rollback:** Vor dem Neustart wird der alte Stand gemerkt (`data/update.pending`), auch bei automatischen Updates. Die neue Version
  prüft ihre Weboberfläche; antwortet sie nicht, setzt `scripts/n8-update-guard.sh` (neu als `ExecStartPre` in `n8hotspot.service`)
  nach drei Starts auf den alten Commit zurück. Ergebnis unter *Letztes Update*. `permissions.sh` (von `update.sh` aufgerufen) erneuert
  die Unit.

### 🔐 Sicherheit
- Neue Header: `Content-Security-Policy`, `Strict-Transport-Security` über HTTPS (auch hinter einem Proxy), `Permissions-Policy`,
  `Cross-Origin-Opener-Policy`/`-Resource-Policy`; kein `server: uvicorn` mehr. Die API-Doku war schon aus; zum Entwickeln `N8_API_DOCS=1`.
- Doku mit Beispielen für **Caddy** und **nginx** als Reverse-Proxy.

### 🧪 Tests
- `tests/test_security.py`: API-Doku aus, Header, HSTS hinter Proxy, kein `server`-Header, Rollback nach drei Starts, Bestätigung nach
  erfolgreichem Start, Unit mit Guard, Kit-Dateien eingebunden.

## [1.3.0] – 2026-11-22

Neue Kopfzeile: statt zwei Leisten (Status-Chips oben, Reiter darunter) gibt es jetzt **ein Menü** und darunter eine schmale
**Statusleiste** – im gleichen Aufbau wie bei HBlink4-FreeRadioID und frn_adn.

### 🧭 Ein Menü in der Kopfzeile
- Die Reiter **🎙️ Live · 📈 Statistics · 🗂️ Talkgroups** sitzen jetzt in der Kopfzeile zwischen Logo/Titel und den Knöpfen rechts.
  Die Kopfzeile bleibt beim Scrollen stehen, die Ansicht wechselst du also von überall.
- **⚙️ Admin** ist nach dem Login (Rolle Admin) ein eigener Menüpunkt, gestrichelt umrandet, statt im Benutzermenü versteckt.
- **🔐 Login** steht ganz rechts. Angemeldet zeigt der Platz deinen **👤 Namen** (Klick öffnet *My account*) und daneben **⏻ Abmelden**.
  Das Aufklappmenü unter dem Namen entfällt.
- Logo und Titel sind etwas kompakter (44 px), der Untertitel wird bei Platzmangel gekürzt statt umzubrechen.
- Unter 1180 px rutschen die Reiter in eine zweite Zeile über die volle Breite; am Smartphone mit kurzen Namen (*Stats*, *TGs*),
  ohne Untertitel, Links und Benutzer als Symbole.

### 🟢 Statusleiste unter dem Menü
- Neue, nur 22 px hohe Leiste direkt unter der Kopfzeile, bewusst kleiner als das Menü: **Live data**, **Modem**, **DMR-Server**
  (Name des Netzes) und rechts der **Modus** (💤 Idle / 📡 DMR / ⏸ Stopped).
- Der Zustand steht als farbiger Punkt davor (grün ok, gelb wartet, rot Fehler, blau aktiv, grau aus); die Texte sind kurz und ohne ✓/✕,
  z. B. *Modem not found*, *N8schicht connecting*, *N8schicht: password wrong*, *Live data offline*.
- Am Smartphone bleibt sie einstellig; die bisherigen Statuspunkte in der Kopfzeile entfallen.

### 🛠️ Technik
- Neue gemeinsame Datei `static/n8-header.css` (identisch mit frn_adn): `.n8-topbar`, `.n8-strip`, `.n8-ss` mit den Punkt-Klassen
  `ok / warn / bad / info / idle / plain`, `.n8-user`, `.n8-logout`, `.n8-menu-admin`, helles Theme und Smartphone-Regeln.
- `userMenu()` entfällt; `renderUser()` baut Name + ⏻, `renderChips()` schreibt in die Statusleiste. Die Element-IDs
  (`chipLive`, `chipModem`, `chipNet`, `chipMode`, `mainTabs`, `tabAdminBtn`) sind gleich geblieben.

### 📚 Doku
- *Live & Statistik*: neuer Abschnitt **Kopfzeile und Statusleiste** mit den Screenshots `header-desktop.png` / `header-mobile.png`.
- Alle Screenshots mit Kopfzeile neu: Live, Statistik, Talkgroups (Desktop und Smartphone) und alle Admin-Seiten.
- Installation und Adminbereich verweisen auf Statusleiste bzw. den Namen oben rechts statt auf das alte Menü.

## [1.2.1] – 2026-11-22

- Website-Site-Icons werden täglich um Mitternacht neu geladen; unter **Admin → Links** gibt es **Refresh site icons now** für einen sofortigen Neuabruf.
- Automatische GitHub-Updateprüfungen laufen zu vollen Stunden.

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
