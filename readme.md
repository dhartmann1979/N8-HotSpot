<p align="center">
  <img src="docs/images/n8-hotspot-banner.png" alt="N8-Hotspot – DMR Die N8schicht" width="100%">
</p>

<p align="center">
  <b>Eigener DMR-Hotspot mit MMDVMHost, DMRGateway und einer Weboberfläche im Design von DMR Die N8schicht</b><br>
  Fertiges Image auf Basis von DietPi · Live-Ansicht · Statistiken · Kalibrierung · Adminbereich · Updates im Browser · alles in SQLite und Python<br>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/github/v/release/dhartmann1979/N8-HotSpot?label=Version&color=5ac8fa" alt="Version"></a>
</p>

<p align="center">
  <a href="#schnellstart">Schnellstart</a> ·
  <a href="docs/de/installation.md">Installation &amp; Image</a> ·
  <a href="docs/de/bedienung.md">Live &amp; Statistik</a> ·
  <a href="docs/de/adminbereich.md">Adminbereich</a> ·
  <a href="docs/de/updates.md">Updates</a> ·
  <a href="docs/de/kalibrierung.md">Kalibrierung</a> ·
  <a href="docs/de/freeradioid.md">FreeRadioID</a> ·
  <a href="docs/de/technik.md">Technik</a> ·
  <a href="docs/de/fehlersuche.md">Fehlersuche</a> ·
  <a href="docs/de/sicherheit.md">Sicherheit</a>
</p>

---

## Was ist das?

**N8-Hotspot** macht aus einem Raspberry Pi mit MMDVM-Board einen DMR-Hotspot, ähnlich wie Pi-Star oder WPSD, aber schlanker und im Look des [N8schicht-Dashboards](https://github.com/dhartmann1979/HBlink4-FreeRadioID). Ab Werk verbindet er sich mit **dmr.die-n8schicht.de**.

| | |
|---|---|
| 📻 **Live wie ein Funkgerät** | Ein Block wie ein digitales Funkgerät: **LEDs** für RX, TX, Modus, Netz und Modem, ein **Display mit beiden Zeitschlitzen** (Rufzeichen, Talkgroup, Sprechzeit, S-Meter, BER-Balken) und die Bilanz des Tages. Dazu schlankes Last Heard. |
| 🎚️ **Vocoder & Signal** | **BER live** des laufenden Funk-Durchgangs, BER/Paketverlust der letzten 40 Durchgänge, RSSI-Verlauf, Sprachqualität des Tages (sauber/hörbar/schlecht) und die AMBE+2-Sprachrahmen über Funk und Netz |
| 🛡️ **FreeRadioID.net** | **Avatare**, **FRID**-Kennzeichen, Profile und die **DMR-ID-Datenbank** direkt aus der FreeRadioID-API; Stationsansicht per Klick auf ein Rufzeichen |
| 🗂️ **Talkgroups** | rund 1.400 Talkgroup-Namen aus der [N8schicht-Liste](https://github.com/dhartmann1979/n8schicht/blob/main/talkgroup_ids.json) überall in der Oberfläche, eigener Tab mit Suche und „hier gehört“ |
| 🔍 **Modem finden** | Scan aller seriellen Schnittstellen mit MMDVM-Abfrage, Erklärung der Ports, Übernahme per Klick |
| 📈 **Statistiken** | Talkgroups, Sprechzeit, RF und Netz, aktivste Stationen; heute, 24 h, 7 oder 30 Tage, als Diagramm und Tabelle |
| 🎛️ **Kalibrierung** | Frequenzabgleich mit MMDVMCal im Browser: BER live, Frequenz per Knopf verschieben, Offset mit einem Klick speichern |
| ⚙️ **Adminbereich** | Station, Modem, Frequenzen, DMR-Server, Zeitschlitze, Expertenzeilen. Dazu Benutzer, Logs, System-Infos, Neustart. |
| 🧩 **Dienste & Berechtigungen** | schlanke Dienste-Liste (Autostart an/aus, Starten, Stoppen, Neu starten) und **Berechtigungen & sudo prüfen und korrigieren** auf Knopfdruck – das gemeinsame **N8 Admin-Kit** wie im HobbyRadioPortal, adn-frn-server und HBlink4 |
| ⬆️ **Update prüfen · Update jetzt** | Prüfung zu jeder vollen Stunde auf GitHub, Hinweis für Admins, **Update jetzt** mit Passwortabfrage: läuft als root (N8 Admin-Kit) – nur vorspulen, Pakete, Dienste, ini-Dateien, Rechte und sudo, Neustart, Prüfung; antwortet die Weboberfläche nicht, automatisch zurück. Update-Protokoll im Browser, auf Wunsch automatisch nachts |
| 🌐 **Deutsch / Englisch** | Umschalter **DE \| EN** in der Kopfzeile, Standard Deutsch; gilt für alle N8schicht-Oberflächen auf dem Gerät |
| 🎨 **Eigene Farben** | N8 Theme wie im HBlink4-Dashboard: 7 Profile (auch hell), jede Farbe frei wählbar, Export/Import zwischen allen N8-Dashboards |
| 🧭 **Ein Menü + Statusleiste** | Kopfzeile mit Logo, Reitern, Links und Login ganz rechts (ohne Aufklappmenü, **⚙️ Admin** nach dem Login als Menüpunkt); darunter eine schmale Statusleiste für Live-Daten, Modem, DMR-Server und Modus |
| 🔗 **Link-Menü** | eigene Links oben rechts, mit den Favicons der verlinkten Seiten (im Hotspot zwischengespeichert) |
| 👁️ **Sichtbereich** | Die Live-Ansicht ist öffentlich (abschaltbar). Benutzer der Rolle *Viewer* sehen alles, ändern aber nichts. |
| 🔐 **Standard-Login** | `n8schicht` / `n8schicht`. Bis zur Änderung im Adminbereich erscheint eine deutliche Warnung. |
| 🗄️ **SQLite + Python** | Einstellungen, Benutzer, Gespräche und ID-Liste liegen in einer Datenbank; daraus entstehen `MMDVM-Host.ini` und `DMRGateway.ini`. |
| 🧭 **Geführte Einrichtung** | `scripts/setup.sh` fragt Station, Modem, Frequenz, Server, Passwort und FreeRadioID ab, prüft die DMR-ID live bei FreeRadioID und installiert alles |
| 🥧 **DietPi-Image** | `scripts/build-image.sh` baut ein Image mit WLAN, Passwort und auf Wunsch fertigen Hotspot-Einstellungen. Der Pi installiert sich beim ersten Start selbst. |

<p align="center">
  <img src="docs/images/live.png" alt="Live-Ansicht" width="72%">
  &nbsp;
  <img src="docs/images/live-mobile.png" alt="Live-Ansicht am Smartphone" width="22%">
</p>

## Schnellstart

**Variante A – eigenes Image (empfohlen).** Auf einem Linux-PC:

```bash
git clone https://github.com/dhartmann1979/N8-HotSpot
cd N8-HotSpot
sudo ./scripts/build-image.sh
```

Das Image auf eine microSD flashen und den Pi starten. Nach 20–40 Minuten ist der Hotspot unter **http://n8-hotspot.local** erreichbar.

**Variante B – geführt auf einem laufenden Pi** (DietPi, Raspberry Pi OS, Debian):

```bash
git clone https://github.com/dhartmann1979/N8-HotSpot && cd N8-HotSpot
sudo ./scripts/setup.sh
```

Ohne vorher eingetragene Hotspot-Einstellungen geht es im Browser weiter: **Login** `n8schicht` / `n8schicht` → eigenes Passwort setzen → **Admin → Settings**. Dort Rufzeichen, DMR-ID, Frequenz und FreeRadioID-Passwort eintragen, dann **Save** und **Restart now**.

<p align="center">
  <img src="docs/images/build-image.png" alt="Image bauen" width="49%">
  <img src="docs/images/setup-1.png" alt="Geführte Einrichtung" width="49%">
</p>

➡️ Ausführlich: **[Installation & Image](docs/de/installation.md)**

## So sieht es aus

<table>
<tr>
<td width="50%"><img src="docs/images/stats.png" alt="Statistik"><br><b>📈 Statistik</b>: Top-Talkgroups, Verlauf nach Talkgroup oder RF/Netz, aktivste Stationen.</td>
<td width="50%"><img src="docs/images/admin-cal.png" alt="Kalibrierung"><br><b>🎛️ Kalibrierung</b>: BER live, Frequenz verschieben, Offset speichern.</td>
</tr>
<tr>
<td><img src="docs/images/station.png" alt="Stationsansicht"><br><b>🛡️ Stationsansicht</b>: Avatar und Profil von FreeRadioID.net, Gespräche und Talkgroups.</td>
<td><img src="docs/images/admin-settings.png" alt="Einstellungen"><br><b>⚙️ Einstellungen</b>: Station, Modem, DMR-Server, DMR-Modus, Dashboard, Experte.</td>
</tr>
<tr>
<td><img src="docs/images/talkgroups.png" alt="Talkgroups"><br><b>🗂️ Talkgroups</b>: Verzeichnis mit Suche, Namen aus der N8schicht-Liste.</td>
<td><img src="docs/images/serial-scan.png" alt="Modem finden"><br><b>🔍 Modem finden</b>: Scan der seriellen Schnittstellen.</td>
</tr>
<tr>
<td><img src="docs/images/admin-keepalive.png" alt="Keep-Alive"><br><b>💓 Keep-Alive</b>: prüft jede Minute Modem, DMR-Server, MQTT und Weboberfläche, startet neu, Heartbeat.</td>
<td><img src="docs/images/setup-2.png" alt="Zusammenfassung"><br><b>🧭 Geführte Einrichtung</b>: Zusammenfassung, Installation, fertig.</td>
</tr>
<tr>
<td><img src="docs/images/admin-updates.png" alt="Update"><br><b>⬆️ Update</b>: Baum-Menü wie in allen N8-Systemen, Update ohne Passwort, Update-Protokoll.</td>
<td><img src="docs/images/admin-appearance.png" alt="Aussehen"><br><b>🎨 Appearance</b>: Farbprofile, eigene Farben, Vorschau mit Lesbarkeit.</td>
</tr>
<tr>
<td><img src="docs/images/theme-daylight.png" alt="Daylight"><br><b>☀️ Daylight</b>: helles Profil für Tageslicht.</td>
<td><img src="docs/images/admin-links.png" alt="Links"><br><b>🔗 Links</b>: Link-Menü mit Site-Icons.</td>
</tr>
</table>

## Dokumentation

| Anleitung | Inhalt |
|---|---|
| 📦 [Installation & Image](docs/de/installation.md) | Hardware, Image bauen und flashen, geführte Einrichtung, Installation ohne Fragen, erster Start, Aktualisieren |
| 🎙️ [Live & Statistik](docs/de/bedienung.md) | Kopfzeile, das Funkgerät (LEDs, Display, Zeitschlitze), Vocoder & Signal, Last Heard, Talkgroup-Verzeichnis, Statistik-Diagramme |
| 🔐 [Sicherheit & N8 Kit](docs/de/sicherheit.md) | Sicherheits-Header, API-Doku aus, Reverse-Proxy (Caddy/nginx), Sprache DE/EN, Updates mit Prüfung und Rollback |
| ⚙️ [Adminbereich](docs/de/adminbereich.md) | Baum-Menü, Standard-Login, alle Einstellungen, Modem finden, Benutzer, Aussehen, Links, System, Logs, Konfigurationsdateien |
| ⬆️ [Updates & Versionen](docs/de/updates.md) | Update-Prüfung, Update jetzt (N8 Admin-Kit), Update-Protokoll, automatische Updates, Dienste, Berechtigungen & sudo, Keep-Alive, Versionsnummern, [Änderungen](CHANGELOG.md) |
| 🎛️ [Kalibrierung](docs/de/kalibrierung.md) | Frequenz-Offset mit MMDVMCal finden, weitere Tests |
| 🛡️ [FreeRadioID](docs/de/freeradioid.md) | Avatare, FRID, Profile, ID-Datenbank, Stationsansicht |
| 🧩 [Technik](docs/de/technik.md) | Aufbau (MMDVMHost ↔ DMRGateway ↔ MQTT), Dateien, Ports, API, Sicherheit |
| 🩺 [Fehlersuche](docs/de/fehlersuche.md) | Modem, Verbindung, Passwort vergessen, Logs, Sicherung |

## Aktualisieren

Im Browser: **Admin → System → ⬆️ Update → Update jetzt** (ohne Passwort) – der Hotspot prüft stündlich selbst und meldet neue Versionen. Das Update läuft
als root über das N8 Admin-Kit mit Prüfung und automatischem Rückweg; das Protokoll steht gleich daneben
(➡️ [Updates & Versionen](docs/de/updates.md), alle Änderungen in [CHANGELOG.md](CHANGELOG.md)). Auf der Konsole:

```bash
sudo /opt/n8hotspot/scripts/update.sh              # wie „Update jetzt“
sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms  # Berechtigungen & sudo prüfen und korrigieren (einmal nach dem Update von 1.4.x)
sudo /opt/n8hotspot/scripts/update.sh --rebuild    # zusätzlich MMDVMHost, DMRGateway, MMDVMCal neu bauen
```

## Danksagung & Lizenz

- **MMDVMHost, DMRGateway, MMDVMCal** von Jonathan Naylor, G4KLX: [github.com/g4klx](https://github.com/g4klx). Die Programme werden bei der Installation aus dem Quellcode gebaut.
- **DietPi**: [dietpi.com](https://dietpi.com)
- Vorbild für den Funktionsumfang: **Pi-Star** und **WPSD**
- Design, Logo und Betrieb des Servers: **DMR Die N8schicht** · ID-Listen von **FreeRadioID.net** (DO5ALF)

N8-Hotspot steht unter der **GNU GPL v3**, siehe [LICENSE](LICENSE).

<p align="center"><img src="static/n8schicht-icon-192.png" width="96" alt="DMR Die N8schicht"></p>
