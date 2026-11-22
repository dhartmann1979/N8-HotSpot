# ⬆️ Updates & Versionen

[← Übersicht](../../readme.md) · [Installation](installation.md) · [Live & Statistik](bedienung.md) · [Adminbereich](adminbereich.md) · **Updates** · [Kalibrierung](kalibrierung.md) · [FreeRadioID](freeradioid.md) · [Technik](technik.md) · [Fehlersuche](fehlersuche.md)

---

Ab Version **1.1.0** aktualisiert sich N8-Hotspot auf Knopfdruck im Browser. Er sieht selbst nach, ob es auf GitHub
eine neue Version gibt, zeigt dir die Änderungen und startet nach dem Update alle Dienste neu.

## Hinweis auf neue Versionen

<p align="center"><img src="../images/update-banner.png" alt="Hinweis auf ein Update" width="95%"></p>

Einmal pro Stunde fragt der Hotspot bei GitHub nach dem neuesten Stand von `dhartmann1979/N8-HotSpot` (Zweig `main`).
Dabei wird nur die öffentliche Commit-Liste gelesen, es werden **keine Daten über deinen Hotspot** gesendet.

Gibt es etwas Neues, sehen **nur Admins** oben den blauen Balken *Version x.y.z is available*. **Show** öffnet den Tab *Updates*.
Besucher und Viewer bekommen davon nichts mit.

## Admin → Updates

<p align="center"><img src="../images/admin-updates.png" alt="Admin → Updates" width="95%"></p>

Links steht die **Version**:

| Zeile | Bedeutung |
|---|---|
| **Installed** | Versionsnummer aus der Datei `VERSION` und der Commit, auf dem der Hotspot steht |
| **On GitHub** | neueste Version und Commit auf GitHub |
| **Status** | ✓ *Up to date*, ⬆️ *Version … available* oder *Check failed* mit Grund (z. B. kein Internet) |
| **Last check** | wann zuletzt nachgesehen wurde |
| **Source** | woher das Update kommt: der Git-Remote `origin` auf dem Hotspot |

Darunter stehen die **Änderungen der neuen Version**, direkt aus [CHANGELOG.md](../../CHANGELOG.md).
**⟳ Check now** fragt sofort nach, **GitHub ↗** zeigt den Vergleich der beiden Stände.

Rechts sind die **Update settings**:

| Einstellung | Vorgabe | Bedeutung |
|---|---|---|
| **Check for updates** | an | stündliche Prüfung und Hinweis für Admins |
| **Check every (hours)** | 1 | 1 bis 168 Stunden |
| **Install automatically** | aus | neue Versionen ohne Klick installieren (siehe unten) |
| **Hour for automatic updates** | 04:00–04:59 | in dieser Stunde wird automatisch installiert |
| **Restart MMDVMHost & DMRGateway** | an | nach dem Update die ini-Dateien neu schreiben und beide Funkdienste neu starten |
| **Repository / Branch** | `dhartmann1979/N8-HotSpot` / `main` | nur ändern, wenn du einen eigenen Fork benutzt |

## Update now

<p align="center"><img src="../images/update-dialog.png" alt="Update installieren" width="50%"></p>

**⬆️ Update now** fragt zur Sicherheit noch einmal **dein Passwort** ab. Nach 5 falschen Versuchen ist 15 Minuten Pause –
genau wie beim Login. Dann passiert der Reihe nach:

1. **Herunterladen:** `git fetch` vom eingetragenen Remote, danach ein *Fast-Forward* auf **genau den Commit, der dir angezeigt wurde**.
   Ist inzwischen etwas anderes auf GitHub, bricht das Update ab und bittet dich, neu zu prüfen.
2. **Python-Pakete:** nur wenn sich `requirements.txt` geändert hat, werden sie in die eigene Umgebung (`venv`) installiert.
3. **Funkdienste:** `MMDVM-Host.ini` und `DMRGateway.ini` werden neu geschrieben, **MMDVMHost** und **DMRGateway** neu gestartet.
4. **Weboberfläche:** `n8hotspot` startet neu. Die Seite wartet und lädt sich von selbst neu, sobald die neue Version läuft.

Im Dialog siehst du jeden Schritt mit ✓ oder ⚠️. Einstellungen, Benutzer, Statistik und Kalibrierung bleiben erhalten –
sie liegen in `/opt/n8hotspot/data/n8hotspot.db`, nicht im Programmordner.

Ein Update wird **abgelehnt**, wenn

- der Hotspot keine Git-Installation ist (z. B. ein kopierter Ordner) – dann `update.sh` auf der Konsole benutzen,
- Dateien im Programmordner von Hand geändert wurden (sonst wären die Änderungen weg) – `git stash` oder auf der Konsole aktualisieren,
- der Hotspot eigene Commits hat, die es auf GitHub nicht gibt,
- gerade schon ein Update läuft (Pause von 30 Sekunden zwischen zwei Versuchen).

## Automatische Updates

Mit **Install automatically** installiert der Hotspot neue Versionen selbst – genauso wie mit *Update now*, nur ohne Klick:

- nur in der gewählten Stunde (Vorgabe 04:00–04:59 Uhr),
- nur wenn **niemand sendet** (beide Zeitschlitze frei) und **keine Kalibrierung** läuft,
- jedes Update steht im Protokoll unter *Sessions & log* mit dem Benutzer `auto-update`.

Fällt die Stunde in ein QSO, wird es in der nächsten Runde (spätestens nach einer Stunde) noch einmal versucht.

## Neustart der Dienste – ohne Änderung an sudoers

Die Weboberfläche läuft als Benutzer `n8hotspot`, nicht als root. Für Neustarts legt `install.sh` schon bei der Installation
die Datei `/etc/sudoers.d/n8hotspot` an. Sie erlaubt **nur** diese Befehle ohne Passwort:

```text
n8hotspot ALL=(root) NOPASSWD: /usr/bin/systemctl start|stop|restart mmdvmhost.service,
    /usr/bin/systemctl start|stop|restart dmrgateway.service,
    /usr/bin/systemctl start|stop|restart mosquitto.service,
    /usr/bin/systemctl restart n8hotspot.service, /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff
```

(In der Datei steht jeder Befehl einzeln.) Damit kann die Weboberfläche nach einem Update die Dienste neu starten, aber
**keine anderen Programme** als root ausführen. Fehlt die Regel (z. B. bei einer sehr alten Installation), beendet sich die
Weboberfläche nach dem Update selbst, und systemd startet sie wegen `Restart=always` sofort wieder. Die Regel lässt sich jederzeit
neu anlegen mit:

```bash
sudo /opt/n8hotspot/scripts/install.sh
```

Prüfen kannst du sie mit `sudo -l -U n8hotspot`.

## Aktualisieren auf der Konsole

Ohne Browser – oder bei einer Installation ohne Git – geht es wie bisher:

```bash
sudo /opt/n8hotspot/scripts/update.sh              # Weboberfläche (git pull, Python-Pakete, Neustart)
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
