# Änderungen

Alle Versionen von **N8-Hotspot** (DMR Die N8schicht), die neueste oben.
Die Nummern folgen [Semantic Versioning](https://semver.org/lang/de/): `MAJOR.MINOR.PATCH`.
Wie Versionen und Updates funktionieren, steht in [docs/de/updates.md](docs/de/updates.md).

## [1.12.0] – 2026-11-26

### 🌐 Neun Sprachen, neue Kopfleiste und ein Anmeldefenster für alle N8-Systeme (N8 Kit 1.6.0)

**Sprachmenü mit neun Sprachen**
- Statt des Umschalters **DE | EN** gibt es das Sprachmenü **🌐 DE ▾** mit **Deutsch, English, Français, Français (Belgique), Magyar, Svenska,
  Nederlands, Italiano und Español** – in der Kopfleiste und unten im Anmeldefenster. Bedienbar auch mit der Tastatur (↓ ↑, Esc).
- Übersetzt sind über **2200 Texte** der vier N8-Systeme mit den Fachbegriffen des Funkbetriebs (Rufzeichen → *indicatif*, *hívójel*,
  *anropssignal*, *roepnaam*, *nominativo*, *indicativo*; Talkgroup, Time Slot und Color Code bleiben wie im DMR-Alltag), dazu Regeln für
  Zahlen und Zeitangaben („vor 5 Min.“ → „il y a 5 min“, „5 perce“ …). **Français (Belgique)** nutzt das Französische mit belgischen
  Abweichungen (z. B. „GSM“) und dem belgischen Datumsformat.
- **Beim ersten Besuch gilt die Sprache des Browsers**, wenn es eine der neun ist, sonst Deutsch. Die Wahl gilt sofort und per Cookie für alle
  N8-Oberflächen auf demselben Server; `?lang=fr` (bzw. `hu`, `sv`, `nl`, `it`, `es`, `fr-BE`) im Link wählt die Sprache direkt.
- **Datum, Uhrzeit und Zahlen** folgen der Sprache (bisher immer deutsches Format).
- Jede weitere Sprache liegt in einer eigenen Datei `static/n8-i18n-<sprache>.js` (rund 80 KB) und wird **nur geladen, wenn sie gewählt ist** –
  beim ersten Aufruf noch vor dem Anzeigen der Seite, damit nichts auf Deutsch aufblitzt.
- Mit einem Sprach-Scan aller Seiten wurden außerdem Texte gefunden, denen bisher die deutsche oder englische Übersetzung fehlte; sie sind ergänzt.

**Einheitliches Anmeldefenster**
- In allen N8-Systemen dasselbe Fenster: Logo und Titel, Benutzername und Passwort mit **👁** zum Anzeigen, Hinweis bei eingeschalteter
  **Feststelltaste**, Schalter **„Angemeldet bleiben“**, Sprachmenü und ein Hinweis, ob die Verbindung verschlüsselt ist (🔒 HTTPS / HTTP).
- Fehler und Sperren (Login-Sperre des N8 Guard) erscheinen direkt im Fenster, das Fenster wackelt kurz; während der Anmeldung dreht ein
  Ladekreis im Knopf. Esc oder ✕ schließt (außer, wenn das Dashboard privat ist und die Anmeldung verlangt).

**Benutzermenü ▾ in der Kopfleiste**
- Angemeldet zeigt die Kopfleiste **Avatar + Name ▾**. Das Menü darunter: Name, Rolle (Superadmin, Admin, …) und die passenden Einträge –
  Konto bzw. Passwort, Adminbereich und **⏻ Abmelden**. Vorher waren es zwei lose Knöpfe.

**Kopfleiste auf Handy und Tablet**
- Unter 900 px Breite ist die Kopfleiste überall gleich aufgebaut: oben Logo, Titel und rechts Sprache · Links · Anmeldung als kompakte
  Knöpfe, darunter die Reiter als wischbare Leiste. Bisher sah jedes System auf dem Handy anders aus.

**Im N8-Hotspot**
- Benutzermenü mit 🔑 Mein Konto, ⚙️ Admin und Abmelden.
- Ergänzt: die deutsche Übersetzung des Werks-Login-Hinweises („Du nutzt den Werks-Login …“), der Kalibrier-Hinweise und von „x MB von y MB“;
  die englische Übersetzung der Ports-Seite (Weboberfläche, DMR-Server-Port, Live-Daten …).
- Statistik, Talkgroups, Kalibrierung und System zeigen Zahlen und Datum im Format der gewählten Sprache.
- Alle Dateien der Oberfläche tragen die Version im Link (`?v=1.12.0`), damit der Browser nach dem Update die neuen lädt.
- Doku: [Sicherheit & N8 Kit](docs/de/sicherheit.md) – Sprachen, Anmeldefenster, Benutzermenü; Kopfleisten- und Werks-Login-Bilder erneuert.

## [1.11.0] – 2026-11-26

### 🔐 Sicherheits-Update
Prüfung aller N8-Portale auf Sicherheitslücken, Fehler, Flooding, Brute-Force und Hintertüren. Hintertüren wurden keine gefunden. Verbessert:

- **N8 Guard gegen Flooding** – neuer, in allen N8-Systemen gleicher Wächter vor dem Dashboard (`n8_guard.py`, Version 1.0.0):
  Anfragen-Budget je IP-Adresse (API 1200/min, Seiten 600/min, Anmeldung 30/min, WebSocket 60 neue/min und höchstens 24 gleichzeitig),
  darüber `429 Too Many Requests` mit `Retry-After`; zu große Anfragen werden mit `413` abgewiesen, bevor sie gelesen werden (Grenze 64 MB).
  Statische Dateien und die Let's-Encrypt-Prüfung zählen nicht mit. Der Speicher für die Zähler ist begrenzt (höchstens 20 000 IPs),
  damit ein Angriff mit vielen Adressen den Server nicht vollschreibt.
- **Login-Sperre über den N8 Guard:** 5 Fehlversuche für denselben Benutzernamen oder 10 von derselben IP in 15 Minuten sperren 15 Minuten –
  auch für Benutzernamen, die es nicht gibt.
- **Werks-Login:** Solange `n8schicht / n8schicht` gilt, lässt das Dashboard keine Änderungen zu, nur das Ändern des Passworts unter
  *Admin → Benutzer & Zugang*. Bisher wurde nur ein Hinweis gezeigt.
- Tests: Prüfungen für Sperre, Werks-Login und Flooding.
- Doku: [Sicherheit](docs/de/sicherheit.md) ergänzt.

## [1.10.0] – 2026-11-25

### 📻 Grafen und Statistik im Funkgerät
- Die Live-Ansicht ist jetzt **ein einziges Funkgerät über die ganze Browserbreite**: Kopfleiste mit Modell, Tageszahlen und LEDs; darunter
  zwei Displays nebeneinander – **TS1/TS2** (gleich hoch) und **BER live** als zweites Display im selben Stil –; darunter drei
  eingebaute Instrumente **RSSI (Funk)**, **Sprachqualität heute** und **Letzte Durchgänge (BER/Verlust)**; ganz unten die
  Tagesstatistik (Gespräche, Sprechzeit, Funk lokal, Netz, Funk-BER).
- Alle Blöcke einer Reihe gleich hoch; die Grafiken füllen ihren Platz. Bis 1100 px Breite stehen die Displays untereinander und die
  Instrumente 2 + 1, auf dem Handy alles untereinander.
- **LED-Farben wie in allen N8-Systemen:** RX **Magenta**, TX **Rot**, Dienst ok **Grün** – die RX-LED und ein empfangender Slot
  (▼ RX) leuchten jetzt magenta statt grün, die Betriebsart-LED (DMR) grün statt blau; NET und MODEM bleiben grün bei ok.
- Screenshots *live.png* und *live-mobile.png* neu.

## [1.9.1] – 2026-11-25

### 📐 Live-Ansicht symmetrisch
- **TS1 und TS2 sind immer gleich hoch** – auch wenn TS1 beim Simplex-Hotspot nicht genutzt wird („Nicht genutzt · Simplex-Hotspot –
  nur TS2“ jetzt zweizeilig wie ein ruhender Slot) und wenn auf TS2 gerade jemand mit Avatar spricht. Die beiden Slots teilen sich die
  Höhe des Displays.
- **Gleich hohe Blöcke über die ganze Browserbreite:** Die Live-Ansicht ist jetzt ein 2 × 2-Raster – oben *Hotspot* | *BER live*,
  unten *RSSI + Sprachqualität* | *Letzte Durchgänge*. Jede Reihe ist links und rechts gleich hoch (vorher war die rechte Spalte höher
  und RSSI hatte eine große leere Fläche). Die Grafiken füllen den Platz, den sie bekommen, und drücken die Karten nicht mehr auf.
- Auf sehr breiten Bildschirmen (ab 1800 px) etwas mehr Luft, unter 1060 px untereinander in der Reihenfolge Hotspot, BER live, RSSI +
  Sprachqualität, letzte Durchgänge.
- Screenshots *live.png* und *live-mobile.png* neu.

## [1.9.0] – 2026-11-25

### 🔤 Schriftauswahl mit Vorschau – in allen N8-Systemen (N8 Theme 2.1)
- Unter *Darstellung → 🎨 Aussehen* neue **Schriftauswahl mit Vorschau** (Rufzeichen, TG, Frequenz, Umlaute, Ziffern in jeder Schrift):
  **IBM Plex Sans** (neuer Standard, technisch und sehr gut lesbar), Inter, Barlow, Exo 2, Rajdhani oder die Systemschrift. Ein Klick wirkt
  sofort, gespeichert wird mit dem Aussehen.
- Zahlen, Anzeigen und Code stehen jetzt überall in **JetBrains Mono** (`--n8-mono`, auch `--mono`).
- Alle Schriften **selbst gehostet** (`fonts/` neben `n8-theme.js`, Fontsource 5.3.0, Schnitte 400/600/700, Latin + Latin-Extended, SIL OFL 1.1,
  Lizenz je Ordner) – keine Anfrage an Google Fonts oder andere fremde Server; die Sicherheitsregeln (`font-src 'self'`) bleiben unverändert.
- Gemeinsame Dateien `n8-theme.js`/`n8-theme.css` (N8 Theme 2.1) und die Prüfung des Themes um `font` erweitert; Doku um „Schrift“ ergänzt.

## [1.8.4] – 2026-11-25

### 🗑 Abstürze bereinigen – in allen N8-Systemen
- **Admin → System → 💥 Abstürze**: jeder aufgeklappte Befund hat **🗑 Diesen Befund löschen**, unten gibt es **🗑 Alle löschen**
  (bzw. **🗑 Angezeigte löschen**, wenn nach einem Dienst gefiltert ist) – jeweils mit Rückfrage. Gelöscht werden der Eintrag in
  `crashes.jsonl` und das Protokoll `crash/<id>.log`; bei „Alle“ auch Reste und der Gelesen-Stand. Die laufende
  Faulthandler-Datei bleibt. Neue Befunde danach zählen wieder als neu.
- Neue Adresse `POST /api/admin/crashes/delete` (`{"all": true}` oder `{"ids": [...]}`), Konsole `n8-admin.sh crashes-clear`.
- Gemeinsame Bausteine `n8_admin.py`, N8 Kit 1.4.2 (`n8-kit.js`) und `n8-admin.sh` – gleich in allen N8-Systemen; Test `tests/test_crash_delete.py`.

## [1.8.3] – 2026-11-25

### 🐛 Update-Fenster: „Nicht aktualisiert“ statt fälschlich „zurückgenommen“
- Brach ein Update ab, bevor es irgendetwas geändert hatte (z. B. „von Hand geänderte Dateien“), meldete das Update-Fenster trotzdem
  „Das Update wurde zurückgenommen“ und hakte „Dienst startet neu“ ab – irreführend. Jetzt liest es das Ergebnis des Updates
  (`/api/admin/update-log`) und zeigt **„Nicht aktualisiert – es läuft unverändert die bisherige Version“** mit dem Grund. Nur ein
  echter Rückbau heißt weiter „zurückgenommen“ (mit Grund). N8 Kit 1.4.1, gleich in allen N8-Systemen.

## [1.8.2] – 2026-11-25

### 🛠️ Update: fehlende Programmdateien werden wiederhergestellt statt das Update abzubrechen
- „Update jetzt“ (`scripts/n8-admin.sh update`) brach ab mit „Im Programmverzeichnis wurden Dateien von Hand geändert – nichts
  aktualisiert“, wenn im Programmordner nur Dateien **fehlten** (z. B. Doku, LICENSE, `.github` – etwa nach einer Installation, die
  nicht alles kopiert hat). Jetzt stellt das Update **fehlende** Dateien aus git wieder her (`git checkout -- <Datei>`, im Protokoll:
  „N fehlende Programmdatei(en) aus git wiederhergestellt“) und läuft weiter. Wirklich **geänderte** Dateien sind weiterhin ein
  Grund zum Abbruch – nichts von Hand Geändertes geht verloren.
- Gemeinsames N8 Admin-Kit (`scripts/n8-admin.sh`), gleich in allen N8-Systemen.

## [1.8.1] – 2026-11-25

### 🐛 Behoben: nach jedem Update „Modem“ gelb / Modem scheinbar weg
- **Ursache:** MMDVMHost meldet „Modem geöffnet“ (`Modem`-JSON und die Log-Zeile `MMDVM protocol version …`) nur **einmal beim Start**
  über MQTT – ohne `retain`. Das Update startete DMRGateway, **dann MMDVMHost und erst zuletzt die Weboberfläche** neu. Bis die neue
  Weboberfläche wieder mit MQTT verbunden war, war die Meldung längst vorbei: Der Zustand blieb „unbekannt“, Statuszeile und LED
  **Modem** zeigten gelb bzw. blinkten, obwohl das Modem in Ordnung war. Zusätzlich wurde das Modem bei **jedem** Update unnötig
  zurückgesetzt (kurze Funkpause, laufende Durchgänge abgebrochen).
- **Jetzt holt die Weboberfläche den Zustand selbst nach:** Ist er unbekannt und MMDVMHost läuft, liest sie das Journal genau des
  laufenden MMDVMHost-Prozesses (`journalctl _SYSTEMD_UNIT=mmdvmhost.service _PID=…`) und wertet die letzte Zeile „protocol version“
  (offen, mit Firmware) bzw. „Unable to read the firmware version / Cannot open …“ (Fehler) aus. Außerdem zählt **Betriebsart Idle/DMR**
  und jeder **Funkempfang** als „Modem offen“. Die echte `Modem`-Meldung von MMDVMHost hat immer Vorrang.
- **Update startet den Funk-Teil nur noch bei Bedarf neu:** zuerst die Weboberfläche, **MMDVMHost und DMRGateway nur**, wenn sich
  ihre ini-Dateien, Dienst-Dateien oder Programme geändert haben (Prüfsumme vor/nach dem Einspielen) oder sie nicht laufen. Das
  Update-Protokoll sagt „Funk-Teil unverändert – MMDVMHost und DMRGateway laufen weiter“ bzw. „Funk-Teil neu gestartet“.
- Hinweis: Das Update **auf** 1.8.1 läuft noch mit dem alten Ablauf (startet alles neu); die neue Anzeige erkennt das Modem dann
  trotzdem nach wenigen Sekunden. Ab dem nächsten Update bleibt der Funk-Teil ohne Änderungen einfach an.
- Test `test_modem_state_after_web_restart`; Fehlersuche-Tabelle um „Modem gelb nach einem Update“ ergänzt.

## [1.8.0] – 2026-11-25

### 👥 Benutzer & Zugang wie in HBlink4-FreeRadioID
- **👥 Benutzer**, **🔑 Sitzungen** und **📜 Protokoll** sind jetzt drei eigene Einträge mit der gemeinsamen Ansicht des N8 Kit 1.4
  (Vorlage HBlink4): „＋ Benutzer anlegen“ in einer Zeile, Tabelle mit Kürzel, Rolle (Admin/Betrachter) und letzter Anmeldung,
  **Bearbeiten** mit Anzeigename, Passwort, Rolle, gesperrt und Löschen; Sitzungen mit Rolle, IP, Browser, Ablauf und **Abmelden**.

### 🌐 Neue Rubrik „Netz, Ports & Domains“ – wie in N8 Crosslink
- **🔌 Ports**: Web-Port, DMR-Server-Port (UDP, ausgehend, änderbar) und MQTT (intern) an einer Stelle, mit Hinweis, dass der Hotspot
  keine Portfreigabe im Router braucht. Ein eigenes HTTPS hat der Hotspot nicht (Heimnetz). Neue Adressen `GET/POST /api/admin/ports`.

### 🛡️ Absturz-Wächter: Neustart nach einem Update ist kein „Absturz“
- Beendet sich die Weboberfläche nach einem Update selbst, meldet sie das vorher als geplant (`n8_crash.mark_planned`).

## [1.7.1] – 2026-11-25

### 🐛 Behoben: „Fehler -15“ beim Neustart des eigenen Dienstes (Admin → System → Dienste)
- **Ursache:** Startet man die Weboberfläche über *Dienste* neu (oder stoppt sie), beendet systemd **alle** Prozesse des Dienstes – auch das
  gerade laufende `sudo systemctl …`. Das meldete sich mit Rückgabewert −15 (SIGTERM) zurück, die Oberfläche zeigte „Fehler -15“, obwohl
  der Neustart geklappt hatte; im Ereignisprotokoll stand „restart … – Fehler -15“.
- **Jetzt:** Der eigene Dienst wird erkannt (`/proc/self/cgroup`), die Antwort geht zuerst raus, eine Sekunde später wird der Neustart
  ausgelöst. Die Ansicht zeigt „Die Weboberfläche startet neu – einen Moment …“ und lädt sich von selbst neu, sobald sie wieder antwortet.
  Gemeinsamer Baustein (`n8_admin.py`, `n8-kit.js`), gleich in allen N8-Systemen.

### 🖥️ Ganze Browser-Breite: überall genau wie N8 Crosslink
- **Gleicher Seitenrand** in allen N8-Systemen: 12 px links und rechts, Kopfzeile und Inhalt stehen auf den Pixel genau wie in N8 Crosslink
  (vorher je nach System 12–16 px; `n8-kit.css`).

## [1.7.0] – 2026-11-25

### 💥 Neu: Absturz-Erkennung – jeder Absturz wird mit Ursache und Protokoll festgehalten, gemeldet und der Dienst neu gestartet
Gleiche Grundlage in allen N8-Systemen (N8 Kit 1.3, `scripts/n8-admin.sh`, `n8_crash.py`) – ausgelöst durch häufige Abstürze von N8 Crosslink,
bei denen nicht erkennbar war, welcher Teil schuld ist. Überwacht werden hier: MMDVMHost, DMRGateway, MQTT (mosquitto) und die Weboberfläche (`n8hotspot.service`).
- **Absturz-Wächter (systemd, als root):** jeder Dienst bekommt ein Drop-in `n8-crashwatch-<id>.conf` mit `ExecStopPost=+… crash-hook`.
  Nach **jedem** Ende prüft er, ob es geplant war (Stoppen/Neustart von Hand, Update, Keep-Alive, Herunterfahren); alles andere wird
  festgehalten – **Absturz durch ein Signal**, **Fehlercode**, **systemd-Watchdog**, **Speicher voll (OOM)**, **Zeitüberschreitung**,
  **unerwartetes Ende** – mit den letzten 200 Journal-Zeilen, Coredump-Kurzinfo und Python-Stack. systemd startet den Dienst sofort neu
  (Dienste ohne `Restart=` bekommen `Restart=on-failure`); bleibt er ausgefallen (`failed`), startet ihn der Keep-Alive neu (`reset-failed`,
  höchstens 4× je Stunde). Neustarts durch den Keep-Alive werden mit Grund festgehalten.
- **Welcher Teil war es?** Die Python-Dienste melden selbst: **faulthandler** (Stack aller Threads beim harten Ende, auch beim Watchdog),
  **Hänger-Wächter** (Event-Loop steht > 8 s → Stack und Teil, z. B. „Datenbank ← Live-Daten“), abgestürzte Tasks und Threads.
  Teile: Live-Daten (MQTT) · Kalibrierung · Konfiguration (ini) · ID-Listen · Statistik · Datenbank · Update · Modem-Suche · System · Anmeldung · Einstellungen · Webinterface.
- **⚙️ Admin → 🖥️ System → 💥 Abstürze:** alle Befunde mit Zeit, Art, Teil, Ursache und vollständigem Protokoll zum Aufklappen, Zähler je Teil
  (7 Tage, als Filter) und die überwachten Dienste.
- **Hinweisfenster nach der Anmeldung:** neue Befunde erscheinen direkt nach dem Admin-Login als Fenster („Gelesen“, „Später“, „Alle Abstürze
  ansehen“) und als roter Zähler im Admin-Menü, bis sie als gelesen markiert sind.
- Konsole: `sudo /opt/n8hotspot/scripts/n8-admin.sh crashes`; einrichten von Hand: `sudo /opt/n8hotspot/scripts/n8-admin.sh setup-crashwatch` (macht sonst „Update jetzt“, die
  Berechtigungsprüfung oder spätestens der Keep-Alive). Dateien im Datenordner: `crashes.jsonl`, `crash/<id>.log`.
- Neue Adressen (gleich in allen N8-Systemen): `GET /api/admin/crashes`, `GET /api/admin/crashes/<id>`, `POST /api/admin/crashes/ack`.

## [1.6.4] – 2026-11-25

### 🖥️ Ganze Browser-Breite und dieselbe Menüleiste in allen N8-Systemen
- **Volle Breite:** Seiten, Fußzeile nutzen jetzt die **ganze Breite des Browserfensters** (vorher höchstens 1400–1600 Pixel);
  der Rand passt sich der Fensterbreite an (10–24 Pixel).
- **Einheitliche Menüleiste nach dem Vorbild des ADN-FRN-Servers:** gleiche Höhe (64 px), gleiche Glas-Kachel, Logo 46 px, Titel 19 px mit
  Farbverlauf, Untertitel 12 px, das Hauptmenü als Pille in der Mitte (gleiche Knöpfe, gleiche Hervorhebung der aktiven Seite), rechts Links,
  DE | EN und Anmelden/Benutzer in gleicher Größe, darunter die schmale Statusleiste. Das gilt in HobbyRadioPortal, ADN-FRN-Server,
  HBlink4-FreeRadioID, N8 Hotspot und N8 Crosslink gleich (N8 Kit 1.2 „N8 Frame“, gemeinsam in `n8-kit.css`). Auf dem Handy bleibt die
  jeweilige kompakte Kopfzeile.

## [1.6.3] – 2026-11-25

### 🧭 Baum-Menü: anfangs zugeklappt, überall gleich
- Alle Gruppen des Admin-Menüs sind jetzt **standardmäßig zugeklappt** – offen ist nur die Gruppe der gerade gewählten Seite.
  Eine Gruppe, die du aufklappst, bleibt offen, bis du den Browser-Tab schließt (vorher wurde der Zustand dauerhaft gespeichert).
- Das gilt in allen fünf N8-Systemen gleich: HobbyRadioPortal, ADN-FRN-Server, HBlink4-FreeRadioID, N8 Hotspot und N8 Crosslink
  nutzen denselben Baum aus dem N8 Kit, mit denselben Gruppen in derselben Reihenfolge.
- Status-Punkte im Menü (z. B. ● online) stehen schlank rechts statt als Plakette.

## [1.6.2] – 2026-11-25

### 🧭 Frühere Unter-Menüs im Baum-Menü
- **⚙️ Einstellungen** hat jetzt Zweige im Baum: 📻 Station · 📡 Modem · DMR-Netz · DMR-Betrieb · Dashboard · FreeRadioID.net · Experte.
  Ein Klick auf einen Zweig zeigt nur diesen Abschnitt in voller Breite, „Einstellungen“ selbst zeigt wie bisher alle.
- N8 Kit: Einträge im Baum können Zweige haben (`children`); sie klappen mit ihrem Eintrag auf und zu.

## [1.6.1] – 2026-11-25

### 🐛 Fix: Keep-Alive startete einen gesunden Dienst neu („Antwort ist kein JSON“)
- **Ursache:** Macht die Anwendung HTTPS selbst (Let's Encrypt im Dashboard), leitet Port 80 nur noch auf `https://<domain>/` weiter.
  Der Keep-Alive fragte `http://127.0.0.1/api/n8/health`, bekam die Weiterleitung statt der Antwort, meldete „Antwort ist kein JSON“ –
  und startete deswegen MQTT, MMDVMHost oder DMRGateway alle paar Minuten neu (bis zur Grenze von 4× je Stunde). Die Prüfung der Weboberfläche hielt die
  Weiterleitung dagegen fälschlich für „gesund“.
- **Weiterleitungen werden jetzt verfolgt – aber immer zurück auf 127.0.0.1** (gleiches Schema, gleicher Port, gleicher Pfad). So wird
  stets die Anwendung auf diesem Rechner gefragt, nie die öffentliche Adresse (kein Hairpin-NAT, kein Zertifikatsproblem, und
  `/api/n8/health` bleibt „nur lokal“). Eine Weiterleitung ins Leere zählt nicht mehr als „Weboberfläche antwortet“.
- **„Zustand unbekannt“ führt nie mehr zu einem Neustart.** Startet ein Dienst neu, dann nur, wenn die Anwendung ihn ausdrücklich als
  gestört meldet (oder wenn er nicht läuft / sein Port nichts annimmt). Keine oder eine fremde Antwort von `/api/n8/health` wird mit
  ❔ angezeigt und einmal ins Protokoll geschrieben – ob die Weboberfläche selbst lebt, prüft weiterhin ihre eigene Prüfung.
- Gilt für alle fünf N8-Systeme (gemeinsames `scripts/n8-admin.sh`).

> Auf bestehenden Servern genügt „Update jetzt“; danach den Keep-Alive unter *System → 💓 Keep-Alive* wieder fortsetzen, falls er pausiert ist.

## [1.6.0] – 2026-11-25

### 🧭 Neu: Admin-Menü als Baum – in allen fünf N8-Systemen gleich
- Die Reiterleiste im Adminbereich ist einem **Baum-Menü links** gewichen, wie im HobbyRadioPortal. Alle N8-Systeme
  (HobbyRadioPortal, ADN-FRN-Server, HBlink4-FreeRadioID, N8 Hotspot, N8 Crosslink) nutzen jetzt **dieselben Gruppen in derselben
  Reihenfolge**: 📡 Betrieb · 👥 Benutzer & Zugang · 🎨 Darstellung · 🌐 Netz & Domains · 🖥️ System.
- Gruppen lassen sich auf- und zuklappen (der Zustand wird im Browser gemerkt); auf dem Handy wird das Menü zu einer
  aufklappbaren Leiste „☰ <aktueller Bereich>“.
- Hotspot: Einstellungen, Kalibrierung, Protokolle und Konfigurationsdateien unter **Betrieb**; „🖥️ Hardware & Daten“
  unter **System**.

### 🖥️ Neu: Derselbe Bereich „System“ überall
- **⬆️ Update · 🧩 Dienste · 🔐 Berechtigungen & sudo · 💓 Keep-Alive** sind gemeinsame Ansichten des N8 Kit 1.1.0 und sehen in
  allen N8-Systemen gleich aus – mit denselben Texten, Knöpfen und Adressen (`/api/admin/services`, `/api/admin/perms`,
  `/api/admin/perms/fix`, `/api/admin/keepalive`, `/api/admin/update-log`).
- **Update:** Stand, GitHub, „Jetzt prüfen“, „Update jetzt installieren“ und daneben das **Update-Protokoll** mit dem Ergebnis des
  letzten Updates (erfolgreich / zurückgenommen).
  Darunter die **Update-Einstellungen** des Hotspots (Prüfintervall, automatisch installieren, Stunde, Funkdienste neu starten).
- **Dienste:** Zustand, Autostart-Schalter und Starten · Stoppen · Neu starten – nur, was die sudo-Regeln freigeben.
- **Berechtigungen & sudo:** zeigt zuerst nur, was nicht stimmt; die bestandenen Prüfungen klappen auf. **🛠️ Korrigieren**
  repariert und prüft erneut.
- **Keep-Alive:** Zustand je Dienst, Internet, Heartbeat, Einstellungen und Protokoll.

### 🔓 Update ohne Passwort
- **„Update jetzt installieren“ fragt nicht mehr nach dem Passwort.** Eine Admin-Sitzung mit CSRF-Header genügt; installiert
  wird wie bisher als root mit Prüfung und automatischem Zurücksetzen.

### 📐 Symmetrische Blöcke
- Kacheln einer Reihe sind im Adminbereich jetzt **gleich hoch**, die Knöpfe stehen unten bündig; eine einzelne letzte Kachel
  nimmt die volle Breite ein.

### 🧰 Kleinigkeiten
- N8 Kit: Schriften im Menü und auf den Knöpfen werden jetzt richtig gesetzt (die `font`-Kurzform mit `inherit` war ungültig und
  wurde vom Browser verworfen).

### 💓 Neu: Keep-Alive – hohe Verfügbarkeit ohne Zutun
- **Dienste-Wächter:** Ein systemd-Timer (`n8hotspot-keepalive.timer`) prüft **jede Minute als root**, ob jeder Dienst wirklich arbeitet –
  nicht nur „läuft“, sondern die Weboberfläche antwortet, MQTT läuft, das Modem offen ist und DMRGateway mit dem DMR-Server verbunden ist. Bleibt ein Dienst 3 Minuten krank (oder steht er auf `failed`), wird er neu gestartet,
  **höchstens 4× je Stunde** – danach meldet der Keep-Alive „aufgegeben“ statt endlos neu zu starten.
- **Netz-Wiederverbindung:** Fällt das Internet aus (1.1.1.1, 9.9.9.9 und github.com auf Port 443 nicht erreichbar), startet der
  Keep-Alive **nicht** sinnlos neu. Ist das Netz nach mindestens 60 s wieder da, startet er die Netzdienste einmal neu, damit
  alle Verbindungen sofort wieder stehen (abschaltbar).
- **Externer Ping (Heartbeat):** Optional eine Adresse für Uptime Kuma („Push“) oder Healthchecks.io – jede Minute ein Ping,
  wenn alles gesund ist, sonst die Fehler-Adresse. So merkst du auch, wenn der ganze Server weg ist.
- **Von Hand gestoppt bleibt gestoppt:** Wer einen Dienst im Webinterface stoppt, wird vom Keep-Alive nicht übergangen; erst
  „Starten“ gibt ihn wieder frei. Für Wartungen gibt es **⏸ 1 h pausieren**.
- Neue lokale Adresse `/api/n8/health` (nur von 127.0.0.1, nie über einen Proxy) liefert dem Keep-Alive den echten Zustand.
- Eingerichtet von `install`, `update` und `fix-perms`; `check-perms` prüft den Timer mit.

> Auf bestehenden Servern genügt „Update jetzt“ im Webinterface; der Keep-Alive richtet sich dabei selbst ein.

## [1.5.3] – 2026-11-25

### 🐛 Fix: „sudo verweigert“ und „Installiert vX · ?“ nach dem Umstellen auf das N8 Admin-Kit
- **git `safe.directory`:** Seit der Programmordner root gehört, lehnte git ihn für den Dienst-Benutzer ab („dubious ownership“) –
  das Webinterface sah keinen Commit (`?`) und bot kein „Update jetzt“ an. `fix-perms` trägt den Ordner jetzt systemweit ein
  (`git config --system`), `check-perms` prüft es.
- **Webinterface noch mit NoNewPrivileges gestartet:** Die Unit war korrigiert, der laufende Prozess aber noch alt – sudo wurde
  abgelehnt. `check-perms` prüft jetzt den **laufenden** Prozess (`/proc/<pid>/status`), `fix-perms` startet das Webinterface dann
  nach 5 Sekunden selbst neu (auch wenn „Korrigieren“ im Browser gedrückt wurde).
- Die Meldung „sudo verweigert“ zeigt jetzt auch den Grund (letzte Zeile von sudo).

> Einmal auf der Konsole: `sudo git -c safe.directory=/opt/n8hotspot -C /opt/n8hotspot pull --ff-only && sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms`

## [1.5.2] – 2026-11-25

### 🐛 Fix: `n8-admin.sh fix-perms` brach nach „korrigiere …“ ohne Meldung ab
- Im gemeinsamen N8 Admin-Kit endete die Hilfsfunktion für die Ausschlüsse im Programmordner (`prune_args`) mit dem Status des
  letzten Vergleichs. Unter `set -e` beendete das das ganze Skript – **ohne Fehlermeldung**, direkt nach „korrigiere …“.
  Betroffen waren `fix-perms`, „Korrigieren“ im Webinterface und **jedes Update** (Abbruch nach der Zeile „Version: …“, also vor
  Rechten, sudo, Neustart und Prüfung). Die Funktion gibt jetzt immer 0 zurück; im Test korrigiert `fix-perms` alle Fehler und prüft erneut.
- `n8-admin.conf`: Werte aus der Unit (`grep … | cut`) brechen nicht mehr ab, wenn die Zeile fehlt (z. B. kein eigener Port eingetragen).

> **Auf bestehenden Servern einmalig** (das laufende alte Skript kann sich nicht selbst reparieren):
> `sudo git -c safe.directory=/opt/n8hotspot -C /opt/n8hotspot pull --ff-only && sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms`

## [1.5.1] – 2026-11-25

### 📐 Live-Ansicht symmetrisch
- Funkgerät und **Vocoder & Signal** stehen jetzt als **zwei gleich breite, gleich hohe Blöcke** nebeneinander: links das Funkgerät mit
  RSSI und Sprachqualität darunter, rechts *Vocoder & Signal* im selben Gehäuse-Stil (eigene Kopfleiste wie das Funkgerät).
- Die Diagramme *BER live* und *Letzte Durchgänge* wachsen mit der Höhe mit und zeichnen sich bei jeder Größenänderung neu.
- Zeitschlitz-Zeile enger gesetzt: lange Namen und Talkgroups werden gekürzt statt sich zu überlappen (FRID-Marke, kürzerer BER-Balken).
- Screenshots `live.png`, `radio.png`, `signal.png`, `live-mobile.png` neu.

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
