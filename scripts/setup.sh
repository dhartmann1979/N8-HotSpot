#!/usr/bin/env bash
# =============================================================================
#  N8-Hotspot – geführte Einrichtung
#
#    sudo ./scripts/setup.sh
#
#  Fragt Station, Modem, Frequenz, DMR-Server, FreeRadioID und Login ab,
#  installiert alles (scripts/install.sh) und trägt die Werte ein.
#  Erneut aufgerufen, schlägt es die aktuellen Werte vor.
#
#  Umgebungsvariablen: N8_DIR (Standard /opt/n8hotspot), N8_SKIP_BUILD=1,
#  N8_SETUP_ONLY=1 (nur Einstellungen setzen, nichts installieren)
# =============================================================================
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
N8_DIR="${N8_DIR:-/opt/n8hotspot}"
C='\033[0;36m'; G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[1m'; D='\033[2m'; N='\033[0m'
step() { echo; echo -e "${C}━━ Schritt $1/8: $2${N}"; }
ok()   { echo -e "   ${G}✓${N} $*"; }
hint() { echo -e "   ${D}$*${N}"; }
warn() { echo -e "   ${Y}!${N} $*"; }
fail() { echo -e "   ${R}✗ $*${N}"; exit 1; }
ask()  { # ask VAR "Frage" default [secret]
    local var=$1 prompt=$2 def=${3:-} secret=${4:-0} v
    if [ "$secret" = 1 ]; then read -r -s -p "   ? $prompt: " v; echo; else read -r -p "   ? $prompt [${def}]: " v; fi
    printf -v "$var" '%s' "${v:-$def}"; }
yesno() { # yesno VAR "Frage" j|n
    local var=$1 prompt=$2 def=$3 v
    read -r -p "   ? $prompt [$( [ "$def" = j ] && echo J/n || echo j/N )]: " v
    v="${v:-$def}"; case "${v,,}" in j|ja|y|yes) printf -v "$var" 1;; *) printf -v "$var" 0;; esac; }
row()  { local pad=$((22 - ${#1})); printf "   %s%*s %s\n" "$1" "$((pad > 0 ? pad : 0))" "" "$2"; }

[ "$(id -u)" -eq 0 ] || fail "Bitte mit sudo starten: sudo $0"

echo -e "
   ${B}🌙 N8-Hotspot – geführte Einrichtung${N}
   DMR-Hotspot mit MMDVMHost, DMRGateway und Weboberfläche · DMR Die N8schicht
   ${D}Jede Frage hat eine Vorgabe in [Klammern]; Enter übernimmt sie.${N}"

# current values when N8-Hotspot is already installed
CUR="{}"
if [ -x "$N8_DIR/venv/bin/python" ] && [ -f "$N8_DIR/data/n8hotspot.db" ]; then
    CUR="$(cd "$N8_DIR" && sudo -u n8hotspot env N8HS_DATA="$N8_DIR/data" ./venv/bin/python -m n8hotspot show-settings 2>/dev/null || echo '{}')"
    hint "Bestehende Installation gefunden – die aktuellen Werte sind vorgeschlagen."
fi
cur() { python3 -c "import json,sys; d=json.loads(sys.argv[1]); v=d.get(sys.argv[2], sys.argv[3]); print(('j' if v else 'n') if isinstance(v,bool) else v)" "$CUR" "$1" "$2"; }

# ---------------------------------------------------------------------------
step 1 "System"
MODEL="$( { tr -d '\0' < /proc/device-tree/model; } 2>/dev/null || echo "$(uname -m)")"
OSN="$( . /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-Linux}")"
ok "$MODEL · $OSN"
PORTS=""
for p in /dev/ttyAMA0 /dev/ttyACM0 /dev/ttyUSB0; do [ -e "$p" ] && PORTS="$PORTS $p"; done
ok "Serielle Schnittstellen:${PORTS:- keine gefunden}"
echo -e "   ${D}Suche das Modem (fragt jede freie Schnittstelle nach ihrer MMDVM-Firmware) …${N}"
SCAN="$(cd "$SRC" && timeout 40 python3 -m n8hotspot scan-serial 2>/dev/null || echo '[]')"
MODEM_PORT=""; MODEM_DESC=""
eval "$(python3 - "$SCAN" <<'EOF'
import json, shlex, sys
try:
    ports = json.loads(sys.argv[1])
except ValueError:
    ports = []
for p in ports:
    if p.get("modem"):
        print(f"MODEM_PORT={shlex.quote(p['port'])}; MODEM_DESC={shlex.quote(p['modem'].get('description', ''))}")
        break
    if p.get("status") == "busy":
        print(f"MODEM_PORT={shlex.quote(p['port'])}; MODEM_DESC={shlex.quote('in Benutzung von ' + ', '.join(u['name'] for u in p['users']))}")
        break
EOF
)"
if [ -n "$MODEM_PORT" ]; then ok "Modem auf ${B}$MODEM_PORT${N}: $MODEM_DESC"
else hint "Kein Modem geantwortet (GPIO-Hat: erst nach dem Neustart nach der Installation; USB: eingesteckt?)."; fi

# ---------------------------------------------------------------------------
step 2 "Station"
hint "Rufzeichen und DMR-ID bekommst du bei radioid.net; FreeRadioID.net vergibt das Passwort für die N8schicht."
while :; do
    ask DMRID "DMR-ID (7-stellig)" "$(cur station.dmr_id 1234567)"
    [[ "$DMRID" =~ ^[0-9]{7}$ ]] && break
    warn "Bitte genau 7 Ziffern."
done
LOOK="$(cd "$SRC" && python3 -m n8hotspot lookup-id "$DMRID" 2>/dev/null || echo '{}')"
jget() { python3 -c "import json,sys; print(json.loads(sys.argv[1]).get(sys.argv[2], ''))" "$LOOK" "$1"; }
FOUND_CALL="$(jget callsign)"; FOUND_NAME="$(jget name)"; FOUND_CITY="$(jget city)"; FRID_REG="$(jget registered)"
if [ -n "$FOUND_CALL" ]; then
    ok "FreeRadioID kennt die ID: ${B}$FOUND_CALL${N} ${FOUND_NAME:+– $FOUND_NAME }${FOUND_CITY:+($FOUND_CITY)}"
    [ "$FRID_REG" = "True" ] && ok "registriert bei FreeRadioID.net → persönliches Passwort möglich (volle Rechte)" \
                             || hint "nicht bei FreeRadioID.net registriert → Gastzugang, oder unter freeradioid.net registrieren"
fi
DEFCALL="$(cur station.callsign N0CALL)"; [ "$DEFCALL" = "N0CALL" ] && [ -n "$FOUND_CALL" ] && DEFCALL="$FOUND_CALL"
while :; do
    ask CALL "Rufzeichen" "$DEFCALL"; CALL="${CALL^^}"
    [[ "$CALL" =~ ^[A-Z0-9]{3,8}$ ]] && break
    warn "3–8 Buchstaben/Ziffern."
done
while :; do
    ask SUFFIX "Hotspot-Suffix, 2 Ziffern (leer = nur DMR-ID)" "$(cur station.suffix 01)"
    [[ "$SUFFIX" =~ ^([0-9]{2})?$ ]] && break
    warn "Zwei Ziffern oder leer."
done
DEFLOC="$(cur station.location '')"; [ -z "$DEFLOC" ] && DEFLOC="$FOUND_CITY"
ask LOCATION "Standort (Ort oder Locator)" "$DEFLOC"
ok "Hotspot-ID ${B}${DMRID}${SUFFIX}${N}"

# ---------------------------------------------------------------------------
step 3 "Modem & Frequenz"
DEFBOARD="$(cur modem.preset '')"
if [ -z "$DEFBOARD" ] || [ "$CUR" = "{}" ]; then
    DEFBOARD=hs_hat; [[ " $PORTS " == *ttyACM0* ]] && [[ " $PORTS " != *ttyAMA0* ]] && DEFBOARD=hs_usb
    case "$MODEM_PORT" in /dev/ttyACM*|/dev/ttyUSB*) DEFBOARD=hs_usb;; esac
    [[ "$MODEM_DESC" =~ [Dd]ual ]] && { [[ "$MODEM_PORT" == /dev/ttyAMA* ]] && DEFBOARD=hs_dual || DEFBOARD=rpt_usb; }
fi
echo "     1) MMDVM_HS_Hat auf der Stiftleiste (Simplex)      → /dev/ttyAMA0"
echo "     2) MMDVM_HS_Dual_Hat auf der Stiftleiste (Duplex)  → /dev/ttyAMA0"
echo "     3) ZUMspot / HS-Board per USB (Simplex)            → /dev/ttyACM0"
echo "     4) MMDVM-Repeaterboard per USB (Duplex)            → /dev/ttyACM0"
declare -A B2N=([hs_hat]=1 [hs_dual]=2 [hs_usb]=3 [rpt_usb]=4 [custom]=1)
N2B=(x hs_hat hs_dual hs_usb rpt_usb)
while :; do ask BN "Board" "${B2N[$DEFBOARD]:-1}"; [[ "$BN" =~ ^[1-4]$ ]] && break; done
BOARD=${N2B[$BN]}
case $BOARD in hs_hat|hs_dual) PORT=/dev/ttyAMA0;; *) PORT=/dev/ttyACM0;; esac
case "$MODEM_PORT" in /dev/ttyACM*|/dev/ttyUSB*) [[ $BOARD == hs_usb || $BOARD == rpt_usb ]] && PORT=$MODEM_PORT;; esac
DUPLEX=0; [[ $BOARD == hs_dual || $BOARD == rpt_usb ]] && DUPLEX=1
[ -e "$PORT" ] || hint "$PORT gibt es (noch) nicht – bei GPIO-Boards nach dem Neustart, bei USB wenn eingesteckt."
mhz() { python3 -c "import sys; v=float(sys.argv[1].replace(',','.')); hz=round(v*1e6) if v<10000 else round(v); assert 1e8<=hz<=1e9; print(hz)" "$1" 2>/dev/null; }
hz2m() { python3 -c "import sys; print('%.4f' % (int(sys.argv[1])/1e6))" "$1"; }
hint "Nur Frequenzen, die zu deiner Zulassung und zum Bandplan passen (70 cm: übliche Hotspot-Simplex-Frequenzen)."
while :; do ask RXM "$( [ $DUPLEX = 1 ] && echo 'RX-Frequenz in MHz' || echo 'Frequenz in MHz')" "$(hz2m "$(cur modem.rx_freq 438800000)")"
    RXF=$(mhz "$RXM") && break; warn "Bitte z. B. 438.8000 eingeben."; done
TXF=$RXF
if [ $DUPLEX = 1 ]; then
    while :; do ask TXM "TX-Frequenz in MHz" "$(hz2m "$(cur modem.tx_freq "$RXF")")"; TXF=$(mhz "$TXM") && break; warn "Ungültig."; done
fi
CC="$(cur dmr.color_code 1)"
ask CC "Color Code" "$CC"
ok "Board $BN · $PORT · $( [ $DUPLEX = 1 ] && echo Duplex || echo Simplex) · $(hz2m "$RXF") MHz · CC$CC"

# ---------------------------------------------------------------------------
step 4 "DMR-Server"
echo "     1) DMR Die N8schicht  (dmr.die-n8schicht.de:62031)"
echo "     2) anderer HomeBrew-Server"
DEFS=1; [ "$(cur network.preset n8schicht)" = custom ] && DEFS=2
ask SN "Server" "$DEFS"
if [ "$SN" = 2 ]; then
    ask NETHOST "Adresse" "$(cur network.host '')"; ask NETPORT "Port" "$(cur network.port 62031)"
    ask NETNAME "Name (kurz)" "$(cur network.name Server)"; PRESET=custom
else
    NETHOST=dmr.die-n8schicht.de; NETPORT=62031; NETNAME=N8schicht; PRESET=n8schicht
    hint "Passwort: dein persönliches FreeRadioID.net-Passwort (volle Rechte)"
    hint "oder Enter für das Gast-Passwort passw0rd (senden nur auf die Gast-Talkgroups)."
fi
HAVEPW="$(cur network.password '')"
ask NETPW "Passwort$( [ -n "$HAVEPW" ] && echo ' (Enter = bisheriges behalten)')" "" 1
if [ -z "$NETPW" ] && [ -z "$HAVEPW" ]; then NETPW=passw0rd; fi
ok "$NETNAME · $NETHOST:$NETPORT · Passwort $( [ "$NETPW" = passw0rd ] && echo 'Gast' || ([ -z "$NETPW" ] && echo 'unverändert' || echo 'gesetzt'))"

# ---------------------------------------------------------------------------
step 5 "FreeRadioID.net"
hint "Avatare und Profile der Stationen, die du hörst, und die Liste der registrierten IDs (FRID)."
yesno FRAV "Avatare anzeigen" "$(cur frid.avatars j)"
yesno FRPROF "Profile abrufen (Name, Ort)" "$(cur frid.profiles j)"
yesno FRIDS "Registrierte FreeRadioID-IDs laden (FRID-Kennzeichen)" "$(cur frid.ids j)"
ok "Avatare $( [ $FRAV = 1 ] && echo an || echo aus) · Profile $( [ $FRPROF = 1 ] && echo an || echo aus) · ID-Liste FreeRadioID.net"

# ---------------------------------------------------------------------------
step 6 "Weboberfläche & Login"
ask TITLE "Titel" "$(cur dashboard.title 'N8 Hotspot')"
yesno PUBLIC "Live-Ansicht ohne Login sichtbar" "$(cur dashboard.public j)"
FACTORY="$(cur _factory_login j)"
ADMINU=""; ADMINP=""
if [ "$CUR" = "{}" ] || [ "$FACTORY" = j ]; then
    hint "Ab Werk: Benutzer n8schicht / Passwort n8schicht (mit Warnung, bis du es änderst)."
    yesno OWN "Jetzt eigenen Admin anlegen" j
    if [ "$OWN" = 1 ]; then
        ask ADMINU "Benutzername" "${SUDO_USER:-admin}"
        while :; do ask ADMINP "Passwort (min. 8 Zeichen)" "" 1; ask P2 "Wiederholen" "" 1
            [ "$ADMINP" = "$P2" ] && [ ${#ADMINP} -ge 8 ] && [ "$ADMINP" != n8schicht ] && break
            warn "Nicht gleich, zu kurz oder das Werkspasswort."; done
    fi
fi

# ---------------------------------------------------------------------------
step 7 "Zusammenfassung"
row "Rufzeichen / ID" "$CALL · $DMRID$SUFFIX${LOCATION:+ · $LOCATION}"
row "Modem" "Board $BN · $PORT · $( [ $DUPLEX = 1 ] && echo "Duplex RX $(hz2m $RXF) / TX $(hz2m $TXF)" || echo "Simplex $(hz2m $RXF)") MHz · CC$CC"
row "DMR-Server" "$NETNAME ($NETHOST:$NETPORT)"
row "FreeRadioID" "Avatare $( [ $FRAV = 1 ] && echo ja || echo nein), Profile $( [ $FRPROF = 1 ] && echo ja || echo nein), FRID-Liste $( [ $FRIDS = 1 ] && echo ja || echo nein)"
row "Weboberfläche" "$TITLE · öffentlich $( [ $PUBLIC = 1 ] && echo ja || echo nein)"
row "Admin" "${ADMINU:-n8schicht (Werks-Login)}"
yesno GO "So einrichten" j
[ "$GO" = 1 ] || fail "Abgebrochen – nichts geändert."

# ---------------------------------------------------------------------------
step 8 "Installation"
if [ "${N8_SETUP_ONLY:-0}" != 1 ]; then
    if ! N8_DIR="$N8_DIR" N8_QUIET_END=1 bash "$SRC/scripts/install.sh" | sed -u 's/^/  │ /'; then
        fail "install.sh ist fehlgeschlagen (siehe /var/log/n8hotspot-install.log)"
    fi
fi
TMP=$(mktemp); chmod 600 "$TMP"
export N8J_CALL="$CALL" N8J_ID="$DMRID" N8J_SUF="$SUFFIX" N8J_LOC="$LOCATION" N8J_BOARD="$BOARD" N8J_PORT="$PORT" \
       N8J_DUP="$DUPLEX" N8J_RX="$RXF" N8J_TX="$TXF" N8J_CC="$CC" N8J_PRESET="$PRESET" N8J_NAME="$NETNAME" \
       N8J_HOST="$NETHOST" N8J_NPORT="$NETPORT" N8J_PW="$NETPW" N8J_AV="$FRAV" N8J_PROF="$FRPROF" N8J_IDS="$FRIDS" \
       N8J_TITLE="$TITLE" N8J_PUB="$PUBLIC" N8J_AU="$ADMINU" N8J_AP="$ADMINP"
python3 - "$TMP" <<'EOF'
import json, os, sys
e = os.environ
b = lambda k: e.get(k) == "1"
s = {"station.callsign": e["N8J_CALL"], "station.dmr_id": e["N8J_ID"], "station.suffix": e["N8J_SUF"],
     "station.location": e["N8J_LOC"], "modem.preset": e["N8J_BOARD"], "modem.port": e["N8J_PORT"],
     "modem.duplex": b("N8J_DUP"), "modem.rx_freq": e["N8J_RX"], "modem.tx_freq": e["N8J_TX"],
     "dmr.color_code": e["N8J_CC"], "dmr.slot1": b("N8J_DUP"), "dmr.slot2": True,
     "network.enabled": True, "network.preset": e["N8J_PRESET"], "network.name": e["N8J_NAME"],
     "network.host": e["N8J_HOST"], "network.port": e["N8J_NPORT"], "network.password": e.get("N8J_PW", ""),
     "frid.avatars": b("N8J_AV"), "frid.profiles": b("N8J_PROF"), "frid.ids": b("N8J_IDS"),
     "dashboard.title": e["N8J_TITLE"], "dashboard.public": b("N8J_PUB")}
out = {"settings": s, "refresh_ids": True}
if e.get("N8J_AU") and e.get("N8J_AP"):
    out["admin"] = {"username": e["N8J_AU"], "password": e["N8J_AP"]}
json.dump(out, open(sys.argv[1], "w"))
EOF
unset N8J_PW N8J_AP
chown n8hotspot "$TMP"
(cd "$N8_DIR" && sudo -u n8hotspot env N8HS_DATA="$N8_DIR/data" ./venv/bin/python -m n8hotspot apply-setup "$TMP") | sed 's/^/   /'
rm -f "$TMP"
command -v systemctl >/dev/null && systemctl restart dmrgateway mmdvmhost n8hotspot 2>/dev/null || true
ok "Dienste mit den neuen Einstellungen neu gestartet"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo -e "
${G}━━ ✅ Fertig!${N}
   Weboberfläche:  ${B}http://$(hostname).local${N}  oder  ${B}http://${IP}${N}
   Login:          ${B}${ADMINU:-n8schicht}${N}$( [ -z "$ADMINU" ] && echo " / n8schicht  → bitte im Browser ändern")
   Als Nächstes:   Admin → Calibration (Frequenz-Offset finden), dann mit dem Funkgerät loslegen.
"
