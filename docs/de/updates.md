# ⬆️ Updates & Versionen

[← Übersicht](../../readme.md) · [Installation](installation.md) · [Live & Statistik](bedienung.md) · [Adminbereich](adminbereich.md) · **Updates** · [Kalibrierung](kalibrierung.md) · [FreeRadioID](freeradioid.md) · [Technik](technik.md) · [Fehlersuche](fehlersuche.md)

---

Ab Version **1.1.0** aktualisiert sich N8-Hotspot auf Knopfdruck im Browser. Er sieht selbst nach, ob es auf GitHub
eine neue Version gibt, zeigt dir die Änderungen und startet nach dem Update alle Dienste neu.

## Hinweis auf neue Versionen

<p align="center"><img src="../images/update-banner.png" alt="Hinweis auf ein Update" width="95%"></p>

Zu jeder vollen Stunde fragt der Hotspot bei GitHub nach dem neuesten Stand von `dhartmann1979/N8-HotSpot` (Zweig `main`).
Dabei wird nur die öffentliche Commit-Liste gelesen, es werden **keine Daten über deinen Hotspot** gesendet.

Gibt es etwas Neues, sehen **nur Admins** unter der Statusleiste den Hinweis *Update verfügbar: v1.4.0 · … → v1.5.0 · …* mit
**Was ist neu?** (klappt die Änderungen auf), **Jetzt aktualisieren**, **Details** (öffnet *Admin → Updates*) und **Später**
(blendet den Hinweis für diese Version einen Tag aus). Besucher und Viewer bekommen davon nichts mit.

Hinweis, Kachel und Fortschritt kommen aus dem **N8 Kit** und sehen in N8-HotSpot, HBlink4-FreeRadioID, adn-frn-server und
N8 Crosslink gleich aus (siehe [Sicherheit & N8 Kit](sicherheit.md)).

## Admin → Updates

<p align="center"><img src="../images/admin-updates.png" alt="Admin → Updates" width="95%"></p>

Links steht die Kachel **⬆️ Updates**:

| Zeile | Bedeutung |
|---|---|
| **Installiert** | Versionsnummer aus der Datei `VERSION` und der Commit, auf dem der Hotspot steht |
| **Auf GitHub** | neueste Version und Commit, mit *Update verfügbar* oder *aktuell* |
| **Zuletzt geprüft** | wann zuletzt nachgesehen wurde |
| **Automatische Prüfung** | *stündlich zur vollen Stunde*, bei *Install automatically* mit der Stunde fürs Installieren |
| **Letztes Update** | *erfolgreich* oder *zurückgenommen*, mit Versionen und Zeit |
| **Quelle** | woher das Update kommt: der Git-Remote `origin` auf dem Hotspot |

Darunter stehen die **Änderungen der neuen Version** (*Was ist neu*), direkt aus [CHANGELOG.md](../../CHANGELOG.md).
**↻ Jetzt prüfen** fragt sofort nach, **⬆️ Update jetzt installieren** installiert.

Rechts sind die **Update settings**:

| Einstellung | Vorgabe | Bedeutung |
|---|---|---|
| **Check for updates** | an | stündliche Prüfung und Hinweis für Admins |
| **Check every (hours)** | 1 | 1 bis 168 Stunden |
| **Install automatically** | aus | neue Versionen ohne Klick installieren (siehe unten) |
| **Hour for automatic updates** | 04:00–04:59 | in dieser Stunde wird automatisch installiert |
| **Restart MMDVMHost & DMRGateway** | an | nach dem Update die ini-Dateien neu schreiben und beide Funkdienste neu starten |
| **Repository / Branch** | `dhartmann1979/N8-HotSpot` / `main` | nur ändern, wenn du einen eigenen Fork benutzt |

## Update jetzt installieren

<p align="center">
  <img src="../images/update-dialog.png" alt="Update bestätigen" width="42%">
  <img src="../images/update-dialog-done.png" alt="Update läuft" width="42%">
</p>

**⬆️ Update jetzt installieren** (oder **Jetzt aktualisieren** im Hinweis) zeigt die Neuerungen und was passiert, und fragt zur
Sicherheit noch einmal **dein Passwort** ab. Nach 5 falschen Versuchen ist 15 Minuten Pause – genau wie beim Login; ein falsches
Passwort lässt das Fenster offen. Dann siehst du drei Schritte: **Update wird geladen und eingespielt → Dienst startet neu →
Weboberfläche wird geprüft**. Im Einzelnen:

Seit **1.5.0** läuft das Update über das gemeinsame **N8 Admin-Kit** (`scripts/n8-admin.sh`, dasselbe wie im HobbyRadioPortal,
adn-frn-server und HBlink4-FreeRadioID, nach dem Vorbild von N8 Crosslink). Die Weboberfläche schreibt nur eine Anforderung
(`data/update.request`); `n8hotspot-update.path` sieht sie und startet `n8hotspot-update.service` – **als root**, unabhängig
von der Weboberfläche:

1. **Vorspulen:** `git fetch` vom eingetragenen Remote, dann nur ein *Fast-Forward*. Wurden Dateien im Programmordner von Hand
   geändert, bricht das Update ab, ohne etwas zu ändern.
2. **Python-Pakete**, wenn sich `requirements.txt` geändert hat; **Dienste** aus den Vorlagen (`systemd/*.service`, Port bleibt);
   **ini-Dateien** neu geschrieben.
3. **Berechtigungen und sudo** prüfen und korrigieren (`fix-perms`), Update-Units aktuell halten.
4. **Neustart** von DMRGateway, MMDVMHost und der Weboberfläche. Die Seite wartet und lädt sich von selbst neu.
5. **Prüfung:** Antwortet die Weboberfläche nicht innerhalb von 90 Sekunden, geht es **automatisch zurück** auf den alten Stand
   (`git reset --keep`) und alles wird neu gestartet.

Das Ergebnis steht unter **Letztes Update** und mit dem ganzen Ablauf in der Kachel **📜 Update-Protokoll**
(`data/update.log`, `data/update.result`). Das gilt auch für automatische Updates.

<p align="center"><img src="../images/admin-updates.png" alt="Updates mit Update-Protokoll" width="90%"></p>

Einstellungen, Benutzer, Statistik und Kalibrierung bleiben erhalten – sie liegen in `/opt/n8hotspot/data/n8hotspot.db`,
nicht im Programmordner.

> **Von 1.4.x auf 1.5.0:** Das erste Update läuft noch über den alten Weg (als Dienst-Benutzer). Danach einmal auf der Konsole
> `sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms` – das richtet sudo und „Update jetzt“ ein; ab dann geht alles im Browser.

Ein Update wird **abgelehnt**, wenn

- der Hotspot keine Git-Installation ist (z. B. ein kopierter Ordner),
- Dateien im Programmordner von Hand geändert wurden (sonst wären die Änderungen weg) – `git stash`, dann erneut,
- der Hotspot eigene Commits hat, die es auf GitHub nicht gibt,
- gerade schon ein Update läuft (Pause von 30 Sekunden zwischen zwei Versuchen).

## 🔐 Dienste, Berechtigungen & sudo

<p align="center"><img src="../images/admin-system.png" alt="System: Dienste und Berechtigungen & sudo" width="90%"></p>

Unter **Admin → System** stehen seit 1.5.0 zwei Kacheln des N8 Admin-Kits:

**🧩 Dienste** – MMDVMHost, DMRGateway, MQTT (mosquitto), die Weboberfläche und der Update-Auslöser, jeweils mit Zustand,
**Autostart**-Schalter und **↻ Neu starten · ▶ Starten · ■ Stoppen** (die Weboberfläche lässt sich nur neu starten).

**🔐 Berechtigungen & sudo** – *Erneut prüfen* zeigt alle Abweichungen, **Korrigieren** behebt sie (prüfen → korrigieren → erneut
prüfen) und zeigt das Protokoll. Geprüft wird:

| Bereich | Prüfung |
|---|---|
| Dienst-Benutzer | `n8hotspot` vorhanden, ohne Login-Shell, in den Gruppen `dialout` (Modem), `systemd-journal`, `adm`, `gpio`, `i2c`, `spi` (soweit vorhanden) |
| Programm | `/opt/n8hotspot` gehört root und ist für den Dienst **schreibgeschützt**, Skripte 755, `venv` lauffähig |
| Daten | `data/` gehört `n8hotspot` (750); Datenbank und ini-Dateien (Passwort des DMR-Servers) nur für den Dienst (600) |
| systemd | Dienste gehören root (644), laufen nicht als root, „Update jetzt“ (`n8hotspot-update.path`) aktiv, Weboberfläche darf sudo nutzen |
| sudo | installiert, `/etc/sudoers.d` eingebunden, `/etc/sudoers.d/n8hotspot-n8admin` gültig (`visudo`), aktuell und wirksam (`sudo -l`) |
| Modem-Schnittstelle | `n8hotspot` darf `/dev/ttyAMA0` bzw. USB-Modems öffnen, keine Linux- oder Login-Konsole darauf, Bluetooth belegt den UART nicht |

Auf der Konsole:

```bash
sudo /opt/n8hotspot/scripts/n8-admin.sh check-perms    # nur prüfen
sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms      # prüfen → korrigieren → prüfen  (= scripts/permissions.sh)
```

Installer und jedes Update rufen `fix-perms` selbst auf. Nimmt die Korrektur die Linux-Konsole vom UART, ist einmal
`sudo reboot` nötig.

## Automatische Updates

Mit **Install automatically** installiert der Hotspot neue Versionen selbst – genauso wie mit *Update jetzt installieren*, nur ohne Klick:

- nur in der gewählten Stunde (Vorgabe 04:00–04:59 Uhr), mit derselben Prüfung und demselben Rollback,
- nur wenn **niemand sendet** (beide Zeitschlitze frei) und **keine Kalibrierung** läuft,
- jedes Update steht im Protokoll unter *Sessions & log* mit dem Benutzer `auto-update`.

Fällt die Stunde in ein QSO, wird es in der nächsten Runde (spätestens nach einer Stunde) noch einmal versucht.

## sudo: genau diese Befehle

Die Weboberfläche läuft als Benutzer `n8hotspot`, nicht als root. `n8-admin.sh` schreibt `/etc/sudoers.d/n8hotspot-n8admin`
(440, mit `visudo` geprüft, bei jedem Update neu). Sie erlaubt **nur**: `systemctl start|stop|restart|enable|disable` für
`mmdvmhost`, `dmrgateway`, `mosquitto` und `n8hotspot-update.path`, `restart|enable` für `n8hotspot`,
`systemctl start n8hotspot-update.service`, `n8-admin.sh check-perms --json` und `fix-perms` sowie `systemctl reboot|poweroff`.
Keine Shell, keine anderen Programme. Die alte Datei `/etc/sudoers.d/n8hotspot` (bis 1.4) entfernt das erste Update.
Prüfen: `sudo -l -U n8hotspot`.

## Aktualisieren auf der Konsole

Ohne Browser – oder bei einer Installation ohne Git – geht es wie bisher:

```bash
sudo /opt/n8hotspot/scripts/update.sh              # wie „Update jetzt“: vorspulen, Pakete, Dienste, Rechte, Neustart, Prüfung
sudo /opt/n8hotspot/scripts/update.sh --rebuild    # dazu aktuelle MMDVMHost/DMRGateway/MMDVMCal bauen
```

`update.sh` aktualisiert nur N8-Hotspot. Neue Versionen von MMDVMHost, DMRGateway und MMDVMCal (G4KLX) baut nur `--rebuild`.

## Versionsnummern

N8-Hotspot zählt nach [Semantic Versioning](https://semver.org/lang/de/): `MAJOR.MINOR.PATCH`.

| Teil | Wann er steigt | Beispiel |
|---|---|---|
| **MAJOR** | Änderungen, nach denen etwas von Hand angepasst werden muss | 2.0.0 |
| **MINOR** | neue Funktionen, alles läuft weiter wie bisher | 1.1.0 |
| **PATCH** | nur Fehlerbehebungen | 1.1.1 |

Jede Version steht mit allen Änderungen in [CHANGELOG.md](../../CHANGELOG.md). Für eine neue Version:

```bash
# 1. CHANGELOG.md: neuen Abschnitt „## [1.2.0] – JJJJ-MM-TT“ oben einfügen und alles beschreiben
python3 scripts/release.py 1.2.0      # prüft CHANGELOG.md, schreibt VERSION und macht den Commit
git push
```

Nach dem Push legt GitHub (Workflow `.github/workflows/release.yml`) den Tag `v1.2.0` und das Release mit dem Text aus
`CHANGELOG.md` an. Ändert man später den Text im Changelog, wird das Release automatisch angepasst.

---

Weiter: [🎛️ Kalibrierung](kalibrierung.md)
