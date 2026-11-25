# 🎙️ Live & Statistik

[← Übersicht](../../readme.md) · [Installation](installation.md) · **Live & Statistik** · [Adminbereich](adminbereich.md) · [Updates](updates.md) · [Kalibrierung](kalibrierung.md) · [FreeRadioID](freeradioid.md) · [Technik](technik.md) · [Fehlersuche](fehlersuche.md)

---

Dieser Teil ist der **Sichtbereich**: ohne Login sichtbar, solange *Public view* im Adminbereich an ist. Ist er aus, sehen nur angemeldete Benutzer (Admin oder Viewer) etwas.

<p align="center">
  <img src="../images/live.png" alt="Live" width="74%">
  &nbsp;
  <img src="../images/live-mobile.png" alt="Live am Smartphone" width="22%">
</p>

## 🎨 Eine Designsprache mit dem HobbyRadioPortal

Der N8 Hotspot bleibt eigenständig, sieht aber aus wie das [HobbyRadioPortal](https://github.com/dhartmann1979/HobbyRadioPortal):
gleiches Farbsystem (N8 Theme 2), gleiche Kopfzeile mit Statusleiste und seit 1.4.2 die gemeinsame Datei **N8 Look**
(`static/n8-look.css`, identisch im Portal). Sie sorgt für den durchgehenden Hintergrund, die farbig leuchtenden Kacheln
die Abschnittsüberschriften und die Fußzeile als Glaskarte:

<p align="center"><img src="../images/footer.png" alt="Fußzeile im N8 Look" width="90%"></p>

Im Portal kann der Hotspot als Verweis erscheinen (Plugin `hotspot`, Vorgabe aus). Das Portal prüft dann nur,
ob die Oberfläche erreichbar ist, und verlinkt sie im Menü „Links“.

## Kopfzeile und Statusleiste

Oben gibt es **ein** Menü: links Logo, Titel und Untertitel, in der Mitte die Reiter, rechts Links und Anmeldung.
Direkt darunter hängt eine schmale **Statusleiste**, die nur zeigt, wie es den Diensten geht – sie ist bewusst
niedriger als das Menü. Beides bleibt beim Scrollen oben stehen.

<p align="center"><img src="../images/header-desktop.png" alt="Kopfzeile mit Menü und Statusleiste" width="95%"></p>

**Menü**

| Eintrag | Bedeutung |
|---|---|
| Titel, Untertitel | Titel aus dem Adminbereich; darunter Rufzeichen, Hotspot-ID, Frequenz, Color Code |
| **🎙️ Live · 📈 Statistics · 🗂️ Talkgroups** | die Ansichten |
| **⚙️ Admin** | erscheint nach dem Login für Admins als eigener Menüpunkt (gestrichelt umrandet) |
| **🔗 Links ▾** | Link-Menü mit Site-Icons der verlinkten Seiten (im Adminbereich unter *Links* einstellbar) |
| **🔐 Login** | ganz rechts; nach dem Anmelden steht dort dein **👤 Name** (Klick = *My account*, Passwort ändern) und daneben **⏻** zum Abmelden – ohne Aufklappmenü |

**Statusleiste** – ein farbiger Punkt sagt den Zustand: grün = ok, gelb = wartet, rot = Fehler, blau = aktiv, grau = aus.

| Anzeige | Bedeutung |
|---|---|
| **Live data** | Der Browser bekommt Live-Daten. Rot (*Live data offline*): Verbindung zum Hotspot weg; sie wird automatisch wieder aufgebaut. |
| **Modem** | MMDVMHost läuft und hat das Modem geöffnet. Rot: *Modem not found* oder *MMDVMHost stopped*. |
| **N8schicht** (Name des DMR-Servers) | DMRGateway ist beim DMR-Server angemeldet. Gelb: *connecting*; rot mit Grund, z. B. *password wrong*, *timeout* oder *gateway stopped*. |
| **💤 Idle / 📡 DMR** (rechts) | aktueller Modus von MMDVMHost |

Am **Smartphone** rutschen die Reiter in eine zweite Zeile (kurze Namen *Stats*, *TGs*), Links und Benutzer sind nur Symbole.
Die Statusleiste bleibt eine Zeile. Die Fußzeile zeigt © Die N8schicht, die installierte Version mit Commit und deren Datum.

<p align="center"><img src="../images/header-mobile.png" alt="Kopfzeile am Smartphone" width="40%"></p>

<p align="center"><img src="../images/links-menu.png" alt="Link-Menü" width="55%"></p>

## 📻 Das Funkgerät: Zeitschlitze, LEDs, Display

<p align="center"><img src="../images/radio.png" alt="Der Hotspot als Funkgerät: LEDs, Display mit TS1 und TS2" width="80%"></p>

Seit 1.5.0 sieht die Live-Ansicht aus wie ein **digitales Funkgerät**: ein Block mit LED-Leiste, einem Display mit beiden
Zeitschlitzen und der Bilanz des Tages darunter.

**LEDs** (oben rechts im Gehäuse)

| LED | leuchtet | Bedeutung |
|---|---|---|
| **RX** | grün, pulsierend | ein Funkgerät sendet gerade **in den Hotspot** (RF) |
| **TX** | rot | der Hotspot **sendet** gerade – ein Gespräch aus dem Netz geht an deine Funkgeräte |
| **Modus** | blau `DMR` · grau `IDLE` · gelb blinkend `LOCKOUT` · rot `ERROR`/`STOPPED` | Betriebsart von MMDVMHost |
| **NET** | grün verbunden · gelb blinkend verbindet · rot Fehler | Anmeldung von DMRGateway am DMR-Server |
| **MODEM** | grün geöffnet · rot nicht gefunden | Modem von MMDVMHost |

**Display**

- Kopfzeile: Rufzeichen, Frequenz (bei Duplex RX und TX), Color Code, DMR-Server mit Verbindungsstatus, Uhrzeit.
- Je **Zeitschlitz eine Zeile** (TS1, TS2). Ein Simplex-Hotspot nutzt nur **TS2** – TS1 steht dann abgedunkelt als *nicht genutzt*.
  Läuft ein Gespräch, zeigt die Zeile **▼ RX** (grün, aus dem Funk) oder **▲ TX** (rot, aus dem Netz), Avatar, Rufzeichen mit **FRID**,
  Name und Ort, Talkgroup mit Namen und die laufende Sprechzeit. Bei RF zusätzlich ein **S-Meter** (RSSI, ab S9 gelb) und ein
  **BER-Balken** (grün < 1 %, gelb bis 3 %, rot darüber). In Ruhe steht dort, wer zuletzt auf dem Zeitschlitz war.
- Fußzeile: Hotspot-ID, Simplex/Duplex, Modem-Firmware, Standort.
- Darunter **Heute**: Gespräche, Sprechzeit, Funk (lokal), Netz und die mittlere BER über Funk.

## 🎚️ Vocoder & Signal

Rechts neben dem Funkgerät, gleich hoch und im selben Gehäuse-Stil (RSSI und Sprachqualität stehen links unter dem Funkgerät).

<p align="center"><img src="../images/signal.png" alt="Vocoder & Signal: BER live, letzte Durchgänge, RSSI, Sprachqualität" width="90%"></p>

| Karte | Inhalt |
|---|---|
| **BER live** | die Bitfehlerrate des laufenden Funk-Durchgangs Sekunde für Sekunde, mit den Bereichen grün (< 1 %, sauber), gelb (1–3 %, hörbar) und rot (> 3 %, der AMBE+2-Vocoder kämpft). Nach dem Durchgang bleibt die Kurve stehen, bis der nächste kommt. Netz-Durchgänge haben keine BER – die misst nur das Modem. |
| **Letzte Durchgänge** | ein Balken je Durchgang (die letzten 40): bei Funk die BER (Farbe wie oben), bei Netz der Paketverlust (blau). Mit der Maus über einen Balken: Zeit, Rufzeichen, Wert. |
| **RSSI (Funk)** | Empfangsstärke der Funk-Durchgänge von heute in dBm, dazu der Mittelwert |
| **Sprachqualität heute** | Anteil sauberer, hörbar gestörter und schlechter Funk-Durchgänge; Ø und max. BER, Ø Paketverlust im Netz und die **Sprachrahmen** (AMBE+2, 50 je Sekunde) über Funk und Netz sowie die geschätzt im Netz verlorenen |

Die Werte kommen aus `GET /api/signal` (Sichtbereich).

## Last Heard

Schlank, eine Zeile je Gespräch – zuerst die letzten 12, mit **Mehr anzeigen** bis zu 40: Zeit, Avatar, 📻/🌐 Quelle und Rufzeichen
mit Name (**FRID** = bei FreeRadioID.net registriert), Zeitschlitz, Ziel (Talkgroup oder 👤 Einzelruf), Dauer.
- **Qualität:** bei RF die BER als farbige Marke (grün < 1 %, gelb < 3 %, rot darüber) und die RSSI; bei Netz-Gesprächen der Paketverlust.
- **Filter:** Mit *Alle / 📻 Funk / 🌐 Netz* zeigst du nur lokale oder nur Netz-Gespräche.

## Stationsansicht

Ein Klick auf ein Rufzeichen, egal ob in Last Heard, im Display (Zeitschlitz) oder in der Statistik, zeigt großen Avatar, FreeRadioID-Profil, Gespräche und Talkgroups dieser Station auf deinem Hotspot. Mehr dazu unter [FreeRadioID](freeradioid.md#stationsansicht).

<p align="center"><img src="../images/station.png" alt="Stationsansicht" width="60%"></p>

## 🗂️ Talkgroups

<p align="center">
  <img src="../images/talkgroups.png" alt="Talkgroup-Verzeichnis" width="72%">
  &nbsp;
  <img src="../images/talkgroups-mobile.png" alt="Talkgroups am Smartphone" width="22%">
</p>

Der Tab **🗂️ Talkgroups** (am Smartphone „TGs“) ist das Verzeichnis aller Talkgroups. Die Namen kommen aus der **Talkgroup-Liste der N8schicht** ([`talkgroup_ids.json`](https://github.com/dhartmann1979/n8schicht/blob/main/talkgroup_ids.json), rund 1.400 Einträge) und deinen eigenen Namen aus dem Adminbereich (*own*).

- **Suche** nach Nummer (Anfang, z. B. `262`) oder Namen (z. B. `bayern`)
- **📻 Heard here**: nur Talkgroups, die dein Hotspot in den letzten 30 Tagen gehört hat, sortiert nach Sprechzeit, mit Gesprächen und „zuletzt gehört“
- **✏️ Own names**: nur deine eigenen Namen

<p align="center">
  <img src="../images/talkgroups-heard.png" alt="Gehörte Talkgroups" width="48%">
  <img src="../images/talkgroups-search.png" alt="Suche" width="48%">
</p>

Die Namen stehen auch überall sonst: im Display (Zeitschlitz), in Last Heard, in der Statistik und in der Stationsansicht. Die Liste wird täglich mit der ID-Liste aktualisiert. Bis dahin nutzt der Hotspot eine mitgelieferte Kopie, die Namen gibt es also auch ohne Internet.

## 📈 Statistik

<p align="center"><img src="../images/stats.png" alt="Statistik" width="95%"></p>

| Element | Inhalt |
|---|---|
| Zeitraum | Heute · 24 h · 7 Tage · 30 Tage |
| Messgröße | ⏱️ Sprechzeit oder 📞 Anzahl Gespräche |
| Kennzahlen | Gespräche, Sprechzeit, Anteil RF, verschiedene Stationen |
| Top talkgroups | die 10 meistgenutzten Talkgroups |
| Activity | pro Stunde oder Tag; umschaltbar zwischen **Talkgroups** (Top 5 farbig, Rest grau) und **RF / Network** |
| Tabellen | alle Talkgroups mit Anteil · aktivste Stationen |

<p align="center">
  <img src="../images/stats-hover.png" alt="Werte beim Überfahren" width="48%">
  <img src="../images/stats-rf-net.png" alt="RF und Netz" width="48%">
</p>

Fährst du mit der Maus über Säulen oder Balken, erscheinen die genauen Werte. Eine Talkgroup behält ihre Farbe, auch wenn du den Zeitraum wechselst. Gespeichert werden die Gespräche 30 Tage lang; das lässt sich im Adminbereich ändern.

<p align="center"><img src="../images/stats-mobile.png" alt="Statistik am Smartphone" width="26%"></p>

---

Weiter: [⚙️ Adminbereich](adminbereich.md)
