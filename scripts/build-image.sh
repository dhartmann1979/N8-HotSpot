#!/usr/bin/env bash
# =============================================================================
#  N8-Hotspot – eigenes Hotspot-Image auf Basis von DietPi bauen
#
#  Läuft auf einem Linux-PC (Debian/Ubuntu, auch WSL2 mit Root), nicht auf dem Pi:
#    sudo ./scripts/build-image.sh
#
#  Ergebnis: N8-Hotspot-DietPi-<datum>.img.xz zum Flashen (Raspberry Pi Imager,
#  balenaEtcher). Beim ersten Start richtet sich der Pi selbst ein: WLAN,
#  Passwort, Zeitzone, dann MMDVMHost, DMRGateway, MMDVMCal und N8-Hotspot.
#
#  Optionen (sonst wird gefragt):
#    --image DATEI       vorhandenes DietPi-Image (.img oder .img.xz) statt Download
#    --url URL           anderes DietPi-Image laden
#    --hostname NAME     Rechnername (Standard n8-hotspot → http://n8-hotspot.local)
#    --wifi-ssid SSID  --wifi-pass PASSWORT  --wifi-country DE
#    --password PW       Passwort für root/dietpi (SSH)
#    --timezone ZONE     Standard Europe/Berlin
#    --yes               nichts fragen, Standardwerte nehmen
# =============================================================================
set -euo pipefail

URL="https://dietpi.com/downloads/images/DietPi_RPi234-ARMv8-Bookworm.img.xz"
IMAGE=""; HOST="n8-hotspot"; SSID=""; WPASS=""; COUNTRY="DE"; PW=""; TZ_="Europe/Berlin"; YES=0
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$REPO/build}"

C='\033[0;36m'; G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[1m'; N='\033[0m'
step() { echo; echo -e "${C}━━ $*${N}"; }
ok()   { echo -e "   ${G}✓${N} $*"; }
fail() { echo -e "   ${R}✗ $*${N}"; exit 1; }
ask()  { local var=$1 prompt=$2 def=${3:-} secret=${4:-0} v
         if [ "$YES" = 1 ] || [ -n "${!var}" ]; then [ -n "${!var}" ] || printf -v "$var" '%s' "$def"; return 0; fi
         if [ "$secret" = 1 ]; then read -r -s -p "   ? $prompt: " v; echo; else read -r -p "   ? $prompt [${def}]: " v; fi
         printf -v "$var" '%s' "${v:-$def}"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --image) IMAGE=$2; shift 2;;  --url) URL=$2; shift 2;;  --hostname) HOST=$2; shift 2;;
        --wifi-ssid) SSID=$2; shift 2;;  --wifi-pass) WPASS=$2; shift 2;;  --wifi-country) COUNTRY=$2; shift 2;;
        --password) PW=$2; shift 2;;  --timezone) TZ_=$2; shift 2;;  --yes|-y) YES=1; shift;;
        -h|--help) sed -n '2,24p' "$0"; exit 0;;
        *) fail "Unbekannte Option: $1";;
    esac
done

[ "$(id -u)" -eq 0 ] || fail "Bitte mit sudo starten (zum Einhängen des Images)."
for t in losetup mount xz curl sha256sum tar; do command -v $t >/dev/null || fail "$t fehlt (sudo apt install xz-utils curl util-linux)"; done

echo -e "
   ${B}🌙 N8-Hotspot – Image-Bau${N}
   DietPi + MMDVMHost + DMRGateway + MMDVMCal + Weboberfläche
"
step "1/5 Einstellungen für den ersten Start"
ask HOST "Rechnername" "$HOST"
ask SSID "WLAN-Name (leer = nur Netzwerkkabel)" ""
if [ -n "$SSID" ]; then ask WPASS "WLAN-Passwort" "" 1; ask COUNTRY "WLAN-Land" "$COUNTRY"; fi
ask PW "Passwort für SSH (root/dietpi), leer = dietpi" "" 1
PW="${PW:-dietpi}"
ask TZ_ "Zeitzone" "$TZ_"
ok "Rechnername $HOST · WLAN ${SSID:-aus} · Zeitzone $TZ_"

step "2/5 DietPi-Image"
mkdir -p "$WORK"
if [ -z "$IMAGE" ]; then
    IMAGE="$WORK/$(basename "$URL")"
    if [ ! -f "$IMAGE" ]; then
        curl -fL --progress-bar -o "$IMAGE.part" "$URL" && mv "$IMAGE.part" "$IMAGE"
        if curl -fsL -o "$IMAGE.sha256" "$URL.sha256"; then
            (cd "$WORK" && sha256sum -c "$(basename "$IMAGE").sha256" >/dev/null) && ok "Prüfsumme stimmt" || fail "Prüfsumme falsch – Download wiederholen"
        fi
    fi
fi
[ -f "$IMAGE" ] || fail "Image nicht gefunden: $IMAGE"
OUT_IMG="$WORK/N8-Hotspot-DietPi-$(date +%Y%m%d).img"
case "$IMAGE" in
    *.xz) xz -dc "$IMAGE" > "$OUT_IMG" ;;
    *)    cp "$IMAGE" "$OUT_IMG" ;;
esac
ok "$(basename "$IMAGE") → $(basename "$OUT_IMG")"

step "3/5 Boot-Partition einrichten"
LOOP=$(losetup -Pf --show "$OUT_IMG")
MNT=$(mktemp -d)
cleanup() { umount "$MNT" 2>/dev/null || true; losetup -d "$LOOP" 2>/dev/null || true; rmdir "$MNT" 2>/dev/null || true; }
trap cleanup EXIT
sleep 1
[ -b "${LOOP}p1" ] || partx -a "$LOOP" 2>/dev/null || true      # containers/WSL without udev
if [ -b "${LOOP}p1" ]; then
    mount "${LOOP}p1" "$MNT"
else                                                            # last resort: mount by offset
    START=$(sfdisk -d "$OUT_IMG" | awk -F'[=,]' '/start=/{gsub(/ /,"",$2); print $2; exit}')
    mount -o loop,offset=$((START * 512)) "$OUT_IMG" "$MNT"
fi
[ -f "$MNT/dietpi.txt" ] || fail "Keine dietpi.txt auf der Boot-Partition – ist das ein DietPi-Image?"

setkv() {  # setkv KEY VALUE  (dietpi.txt)
    local k=$1 v=$2
    if grep -q "^$k=" "$MNT/dietpi.txt"; then sed -i "s|^$k=.*|$k=$v|" "$MNT/dietpi.txt"; else echo "$k=$v" >> "$MNT/dietpi.txt"; fi
}
setkv AUTO_SETUP_AUTOMATED 1
setkv AUTO_SETUP_ACCEPT_LICENSE 1
setkv AUTO_SETUP_NET_HOSTNAME "$HOST"
setkv AUTO_SETUP_GLOBAL_PASSWORD "$PW"
setkv AUTO_SETUP_TIMEZONE "$TZ_"
setkv AUTO_SETUP_LOCALE "de_DE.UTF-8"
setkv AUTO_SETUP_KEYBOARD_LAYOUT "de"
setkv AUTO_SETUP_CUSTOM_SCRIPT_EXEC 0
setkv AUTO_SETUP_HEADLESS 1
setkv SURVEY_OPTED_IN 0
setkv CONFIG_SERIAL_CONSOLE_ENABLE 0
if [ -n "$SSID" ]; then
    setkv AUTO_SETUP_NET_WIFI_ENABLED 1
    setkv AUTO_SETUP_NET_WIFI_COUNTRY_CODE "$COUNTRY"
    # dietpi-wifi.txt is sourced by bash: printf %q quotes SSID and key safely
    WF="$MNT/dietpi-wifi.txt"
    grep -v -e '^aWIFI_SSID\[0\]=' -e '^aWIFI_KEY\[0\]=' "$WF" > "$WF.new" || true
    { printf 'aWIFI_SSID[0]=%q\n' "$SSID"; printf 'aWIFI_KEY[0]=%q\n' "$WPASS"; } >> "$WF.new"
    mv "$WF.new" "$WF"
fi
ok "dietpi.txt: automatische Einrichtung, Rechnername, Passwort, Zeitzone${SSID:+, WLAN}"

CFG="$MNT/config.txt"
if [ -f "$CFG" ] && ! grep -q '^# N8-Hotspot' "$CFG"; then
    printf '\n# N8-Hotspot: PL011-UART für das MMDVM-Modem (GPIO 14/15), Bluetooth aus\nenable_uart=1\ndtoverlay=disable-bt\n' >> "$CFG"
fi
[ -f "$MNT/cmdline.txt" ] && sed -i -E 's/console=(serial0|ttyAMA0),[0-9]+ ?//g' "$MNT/cmdline.txt"
ok "config.txt/cmdline.txt: /dev/ttyAMA0 frei für das Modem"

install -m 755 "$REPO/image/Automation_Custom_Script.sh" "$MNT/Automation_Custom_Script.sh"
tar -C "$REPO" --exclude=./build --exclude=./data --exclude=./venv --exclude=./.pytest_cache --exclude='*/__pycache__' \
    -czf "$MNT/n8hotspot.tar.gz" .
HASH="$(git -C "$REPO" log -1 --format=%h 2>/dev/null || true)"
ok "N8-Hotspot${HASH:+ ($HASH)} und Installationsskript für den ersten Start"
sync
cleanup
trap - EXIT

step "4/5 Packen"
rm -f "$OUT_IMG.xz"
xz -T0 -6 "$OUT_IMG"
ok "$(basename "$OUT_IMG").xz ($(du -h "$OUT_IMG.xz" | cut -f1))"

step "5/5 Prüfsumme"
(cd "$WORK" && sha256sum "$(basename "$OUT_IMG").xz" > "$(basename "$OUT_IMG").xz.sha256")
ok "$(cut -c1-16 "$OUT_IMG.xz.sha256")…"

echo -e "
${G}━━ ✅ Image fertig:${N} ${B}$OUT_IMG.xz${N}

   1. Mit dem Raspberry Pi Imager (\"Eigenes Image\", ohne OS-Anpassung) oder balenaEtcher auf eine microSD flashen.
   2. Hotspot-Board aufstecken, microSD in den Pi, Strom an.
   3. Etwa 20–40 Minuten warten (DietPi-Einrichtung, Bau von MMDVMHost, ein Neustart).
   4. Im Browser ${B}http://$HOST.local${N} öffnen, Login ${B}n8schicht${N} / ${B}n8schicht${N}.
"
