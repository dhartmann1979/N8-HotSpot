# 🧩 Technik

[← Übersicht](../../readme.md) · [Installation](installation.md) · [Live & Statistik](bedienung.md) · [Adminbereich](adminbereich.md) · [Kalibrierung](kalibrierung.md) · **Technik** · [Fehlersuche](fehlersuche.md)

---

## Aufbau

```
 Funkgerät ))) Modem ── UART ── MMDVMHost ──UDP 62032⇄62031── DMRGateway ──HomeBrew/UDP── dmr.die-n8schicht.de
                                    │                              │
                                    └── MQTT (mosquitto, localhost) ┘
                                                  │  mmdvm/json, mmdvm/log, dmr-gateway/json, dmr-gateway/log
                                                  ▼
                                  N8-Hotspot (Python, FastAPI) ── SQLite ── Browser (HTTP + WebSocket)
                                                  │
                                                  └─ schreibt MMDVM-Host.ini / DMRGateway.ini, steuert systemd, MMDVMCal
```

- **MMDVMHost** (G4KLX) spricht mit dem Modem. Aktuelle Versionen verbinden sich nur über **DMRGateway** mit einem DMR-Server.
- **DMRGateway** meldet sich am Server an: HomeBrew-Protokoll mit Passwort und Options, der FreeRadioID-Login der N8schicht inbegriffen. Alle Talkgroups und Einzelrufe beider Zeitschlitze werden durchgereicht (`PassAllTG`/`PassAllPC`).
- **Live-Daten:** Beide Programme veröffentlichen ihre Daten als **JSON über MQTT**: Gesprächsbeginn/-ende mit Quelle, IDs, Dauer, BER, RSSI, Paketverlust; Modus; Modem; Verbindung zum Server mit Grund bei Fehlern. N8-Hotspot abonniert das, speichert jedes beendete Gespräch in SQLite und schickt alles per WebSocket an die Browser.

## Dateien und Dienste

| Was | Wo |
|---|---|
| Weboberfläche | `/opt/n8hotspot` (Python-Paket `n8hotspot/`, Oberfläche `static/`) |
| Datenbank | `/opt/n8hotspot/data/n8hotspot.db` mit den Tabellen `settings`, `users`, `sessions`, `audit`, `calls`, `dmrids`, `frid_ids` (FreeRadioID-registrierte IDs), `frid_avatars` (192-px-WebP), `tg_list` (Talkgroup-Namen der N8schicht) |
| Erzeugte Konfiguration | `/opt/n8hotspot/data/MMDVM-Host.ini`, `DMRGateway.ini` |
| ID-Liste für MMDVMHost | `/opt/n8hotspot/data/DMRIds.dat` (aus der FreeRadioID-Liste, täglich neu) |
| Programme | `/usr/local/bin/MMDVMHost`, `DMRGateway`, `MMDVMCal`; Quellen in `/usr/local/src/g4klx` |
| Dienste | `mmdvmhost`, `dmrgateway`, `mosquitto`, `n8hotspot` (alle als Benutzer `n8hotspot`, außer mosquitto) |
| sudo-Regel | `/etc/sudoers.d/n8hotspot`: nur Start/Stopp/Neustart dieser Dienste, Reboot, Shutdown |
| Logs | `journalctl -u mmdvmhost -u dmrgateway -u n8hotspot`; Installation in `/var/log/n8hotspot-install.log` |

## Externe Dienste

| Was | Woher | Wann |
|---|---|---|
| DMR-ID-Liste | `freeradioid.net/api/subscriber_ids.csv` (oder radioid.net) | täglich, Uhrzeit einstellbar |
| FreeRadioID-registrierte IDs | `freeradioid.net/api/local_subscriber_ids.json` | mit der ID-Liste |
| Avatare | `freeradioid.net/api/idimg-<ID>.png` | wenn eine registrierte Station gehört wird; neu geprüft wöchentlich bzw. täglich |
| Profile | `freeradioid.net/api/dmr/user/?id=<ID>` | beim Öffnen der Stationsansicht, eine Stunde zwischengespeichert |
| Talkgroup-Namen | `raw.githubusercontent.com/dhartmann1979/n8schicht/main/talkgroup_ids.json` (Kopie liegt bei) | mit der ID-Liste |
| Quellcode G4KLX | `github.com/g4klx` | nur bei Installation/Update |

## Ports

| Port | Dienst | Erreichbar |
|---|---|---|
| TCP 80 | Weboberfläche | im lokalen Netz |
| UDP 62031/62032 | MMDVMHost ⇄ DMRGateway | nur localhost |
| TCP 1883 | MQTT | nur localhost |
| UDP (ausgehend) | DMRGateway → Server, z. B. 62031 | ins Internet |

Eingehende Ports im Router sind **nicht** nötig.

## Sicherheit

- **Werks-Login** `n8schicht`/`n8schicht` mit Warnung, bis das Passwort geändert ist; das Werkspasswort lässt sich nicht erneut setzen.
- **Passwörter** werden mit **scrypt** gehasht. Sitzungen sind zufällige Tokens; die Datenbank speichert nur deren SHA-256. Das Cookie ist `HttpOnly` und `SameSite=Strict`.
- Ändernde Anfragen brauchen den Header `X-N8: 1` (Schutz gegen CSRF).
- **Login-Sperre:** Nach 5 Fehlversuchen ist der Login 15 Minuten gesperrt. Das Protokoll zeichnet alle Änderungen mit IP auf.
- **Passwörter in den Configs:** Das DMR-Passwort steht nur in `DMRGateway.ini` (lesbar nur für `n8hotspot`); Anzeigen in der Oberfläche blenden es aus.
- Die Weboberfläche ist für das **lokale Netz** gedacht. Nicht per Portweiterleitung ins Internet stellen, sondern bei Bedarf über VPN zugreifen.

## API

Alle Antworten sind JSON. Die Oberfläche nutzt dieselbe API.

| Methode & Pfad | Zugriff | Inhalt |
|---|---|---|
| `GET /api/info` | Sichtbereich | Station, Frequenz, Netz, Talkgroup-Namen, angemeldeter Benutzer |
| `GET /api/live` | Sichtbereich | Modem, Modus, Verbindung, aktive Zeitschlitze, Last Heard, Dienste |
| `GET /api/stats?range=today\|24h\|7d\|30d` | Sichtbereich | Statistik wie in den Diagrammen |
| `GET /api/station/{id}` | Sichtbereich | Stationsansicht: FreeRadioID-Profil, Gespräche und Talkgroups der letzten 30 Tage, letzte Gespräche |
| `GET /api/avatar/{id}` | Sichtbereich | Avatar (WebP) für bei FreeRadioID registrierte IDs, sonst 404 |
| `GET /api/talkgroups` | Sichtbereich | alle Talkgroup-Namen (Liste + eigene) und was der Hotspot in 30 Tagen darauf gehört hat |
| `POST /api/admin/serial/scan` | Admin | serielle Schnittstellen mit Typ, USB-Daten, Belegung und MMDVM-Antwort |
| `WS /ws` | Sichtbereich | Live-Ereignisse `status`, `slot`, `heard`; für Admins zusätzlich `log`, `cal` |
| `POST /api/auth/login`, `logout`, `password` | – | Anmeldung, eigenes Konto |
| `GET/POST /api/admin/settings`, `POST /api/admin/apply` | Admin | Einstellungen lesen/speichern, Dienste neu starten |
| `GET /api/admin/config-files` | Admin | erzeugte ini-Dateien (Passwörter ausgeblendet) |
| `…/admin/users`, `…/sessions`, `…/audit` | Admin | Benutzer, Sitzungen, Protokoll |
| `GET /api/admin/system`, `POST …/service`, `…/power`, `…/idlist/refresh` | Admin | System, Dienste, Reboot/Shutdown, ID-Liste und FreeRadioID-Liste |
| `GET /api/admin/logs`, `…/journal?service=` | Admin | Live-Log, systemd-Journal |
| `…/admin/cal`, `…/cal/start`, `…/cal/key`, `…/cal/freq`, `…/cal/save`, `…/cal/stop` | Admin | Kalibrierung |

## Entwicklung und Demo-Modus

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt pytest httpx    # Pillow verkleinert die Avatare
N8HS_DEMO=1 N8HS_DATA=/tmp/n8demo N8HS_PORT=8090 ./venv/bin/python -m n8hotspot   # ohne Modem, simulierter Verkehr
./venv/bin/python -m pytest -q
```

Im Demo-Modus zeigt N8-Hotspot ausgedachte Stationen; die Avatare sind gezeichnete Landschaften statt echter Fotos. Er erzeugt dieselben MQTT-Nachrichten, die MMDVMHost und DMRGateway schicken würden, und füllt die Statistik. Die Kalibrierung läuft dann gegen `tools/fake_mmdvmcal.py`. Damit sind auch die Screenshots in dieser Doku entstanden. Getestet wurde zusätzlich mit echtem MMDVMHost (Null-Modem), DMRGateway und einem HBlink4-Server der N8schicht: Anmeldung, Gastzugang und falsches Passwort.

---

Weiter: [🩺 Fehlersuche](fehlersuche.md)
