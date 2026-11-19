# 🩺 Fehlersuche

[← Übersicht](../../readme.md) · [Installation](installation.md) · [Live & Statistik](bedienung.md) · [Adminbereich](adminbereich.md) · [Kalibrierung](kalibrierung.md) · [FreeRadioID](freeradioid.md) · [Technik](technik.md) · **Fehlersuche**

---

## Die häufigsten Fälle

| Symptom | Ursache | Lösung |
|---|---|---|
| **✕ Modem** rot | falscher Port, Board nicht gesteckt, serielle Konsole oder Bluetooth belegen `/dev/ttyAMA0` | *Settings → Modem → 🔍 Find*: zeigt, wo ein Modem antwortet, und trägt den Port mit **Use** ein. Nach der Installation einmal neu starten. |
| **✕ N8schicht: password wrong** | falsches Passwort beim Server | *Settings → DMR network → Password*: bei der N8schicht das FreeRadioID-Passwort oder das Gast-Passwort |
| **✕ N8schicht: login** | Der Server kennt die ID nicht oder lässt sie nicht zu | DMR-ID und Hotspot-Suffix prüfen (*Station*) |
| **✕ N8schicht: config** | Die ID ist schon verbunden, z. B. ein zweiter Hotspot mit gleicher ID | anderes Hotspot-Suffix nehmen |
| **✕ N8schicht: timeout** | Server nicht erreichbar | Internet, Adresse und Port prüfen; ausgehendes UDP darf nicht gesperrt sein |
| Hotspot empfängt schlecht, BER hoch | Frequenz-Offset | [Kalibrierung](kalibrierung.md) |
| Nur Gast-Talkgroups gehen | mit dem Gast-Passwort angemeldet | persönliches Passwort von [FreeRadioID.net](https://freeradioid.net) eintragen |
| **✕ Live data** | Browser hat die Verbindung verloren, oder der Dienst `n8hotspot` läuft nicht | Seite neu laden; `sudo systemctl status n8hotspot` |
| Keine Live-Daten, aber Hotspot funktioniert | mosquitto läuft nicht | *System → Services → MQTT broker → Restart* |
| Keine Avatare | Station nicht bei FreeRadioID.net registriert (kein FRID), kein eigenes Bild dort hinterlegt, Avatare abgeschaltet oder kein Internet | *System → FreeRadioID.net*: Zahl der registrierten IDs; *Settings → FreeRadioID.net → Show avatars*; *System → ⟳ Update now* |
| Rufzeichen statt Namen fehlen | ID-Liste noch nicht geladen | *System → DMR ID list → ⟳ Update now*; braucht Internet |
| `http://n8-hotspot.local` geht nicht | Gerät oder Router ohne mDNS (Bonjour) | IP aus dem Router nehmen; Windows braucht ggf. die Bonjour-Dienste |

## Passwort vergessen

Per SSH auf dem Pi:

```bash
cd /opt/n8hotspot
sudo -u n8hotspot env N8HS_DATA=/opt/n8hotspot/data ./venv/bin/python -m n8hotspot reset-password n8schicht
```

Damit setzt du ein neues Passwort für den Benutzer, entsperrst ihn und beendest seine Sitzungen. Gibt es den Benutzer nicht, wird er als Admin angelegt. Statt `n8schicht` geht jeder andere Benutzername.

## Logs ansehen

```bash
journalctl -u mmdvmhost -u dmrgateway -n 100 --no-pager       # die beiden G4KLX-Programme
journalctl -u n8hotspot -n 100 --no-pager                       # Weboberfläche
cat /var/log/n8hotspot-firstboot.log                            # erster Start des Images
mosquitto_sub -t '#' -v                                         # Live-Daten mitlesen (apt install mosquitto-clients)
```

Im Browser: **Admin → Logs** (live) und dort **Show system journal**.

## Sichern und wiederherstellen

Alles Wichtige steckt in `/opt/n8hotspot/data/n8hotspot.db`. Zum Sichern braucht es das Paket `sqlite3`:

```bash
sudo apt install sqlite3
sudo sqlite3 /opt/n8hotspot/data/n8hotspot.db ".backup '/home/dietpi/n8hotspot-$(date +%F).db'"
```

**Wiederherstellen:** Dienst stoppen (`sudo systemctl stop n8hotspot`), Datei zurückkopieren, Besitzer setzen (`sudo chown n8hotspot: /opt/n8hotspot/data/n8hotspot.db`) und Dienst starten. Die ini-Dateien schreibt N8-Hotspot beim Start neu.

## Neu installieren, ohne Daten zu verlieren

```bash
sudo N8_SKIP_BUILD=1 /opt/n8hotspot/scripts/install.sh
```

Datenbank und Einstellungen bleiben erhalten.

---

[← Zurück zur Übersicht](../../readme.md)
