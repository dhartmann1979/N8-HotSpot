#!/usr/bin/env bash
# =============================================================================
#  N8-Hotspot – Installation auf DietPi / Raspberry Pi OS / Debian
#
#  Installiert: mosquitto (MQTT), MMDVMHost, DMRGateway und MMDVMCal (G4KLX,
#  aus dem Quellcode), die Weboberfläche N8-Hotspot und die systemd-Dienste.
#
#    sudo ./scripts/install.sh
#
#  Umgebungsvariablen (optional):
#    N8_DIR=/opt/n8hotspot      Zielverzeichnis
#    N8_PORT=80                 Web-Port
#    N8_SKIP_BUILD=1            MMDVMHost/DMRGateway/MMDVMCal nicht neu bauen
#    N8_SKIP_UART=1             serielle Schnittstelle des Raspberry Pi nicht anfassen
#    MMDVMHOST_REF / DMRGATEWAY_REF / MMDVMCAL_REF   Git-Stand (Branch, Tag, Commit)
# =============================================================================
set -euo pipefail

N8_DIR="${N8_DIR:-/opt/n8hotspot}"
N8_PORT="${N8_PORT:-80}"
SVC_USER=n8hotspot
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR=/usr/local/src/g4klx
LOG=/var/log/n8hotspot-install.log

C='\033[0;36m'; G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[1m'; N='\033[0m'
step()  { echo; echo -e "${C}━━ $*${N}"; }
ok()    { echo -e "   ${G}✓${N} $*"; }
warn()  { echo -e "   ${Y}!${N} $*"; }
fail()  { echo -e "   ${R}✗ $*${N}"; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "Bitte mit sudo starten: sudo $0"
exec > >(tee -a "$LOG") 2>&1

echo -e "
   ${B}🌙 N8-Hotspot – Installation${N}
   MMDVMHost · DMRGateway · MMDVMCal · Weboberfläche im Design von DMR Die N8schicht
"

# ---------------------------------------------------------------------------
step "1/7 Systempakete"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -q --no-install-recommends git ca-certificates build-essential libmosquitto-dev \
    nlohmann-json3-dev mosquitto python3 python3-venv python3-pip sudo avahi-daemon >/dev/null
ok "git, Compiler, mosquitto, Python, avahi (Name.local)"

# ---------------------------------------------------------------------------
step "2/7 Dienst-Benutzer ${SVC_USER}"
if ! id "$SVC_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "/var/lib/$SVC_USER" --shell /usr/sbin/nologin "$SVC_USER"
fi
for g in dialout systemd-journal adm gpio i2c spi; do
    getent group "$g" >/dev/null && usermod -aG "$g" "$SVC_USER"
done
ok "${SVC_USER} (dialout für das Modem, systemd-journal für die Logs)"

# ---------------------------------------------------------------------------
step "3/7 MMDVMHost, DMRGateway und MMDVMCal (G4KLX)"
JOBS=$(nproc)
MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
[ "$MEM_MB" -lt 1500 ] && JOBS=2
[ "$MEM_MB" -lt 600 ] && JOBS=1
build() {   # name repo ref binary_in_repo target
    local name=$1 repo=$2 ref=$3 bin=$4 target=$5
    mkdir -p "$BUILD_DIR"
    if [ -d "$BUILD_DIR/$name/.git" ]; then
        git -C "$BUILD_DIR/$name" fetch -q --depth 50 origin "${ref:-HEAD}"
        git -C "$BUILD_DIR/$name" checkout -q -f FETCH_HEAD
    else
        git clone -q --depth 50 "https://github.com/g4klx/$repo" "$BUILD_DIR/$name"
        [ -n "$ref" ] && git -C "$BUILD_DIR/$name" checkout -q "$ref"
    fi
    echo "   … baue $name ($(git -C "$BUILD_DIR/$name" log -1 --format='%h %ad' --date=short)), dauert auf einem Pi Zero 2 W etwa 10–30 Minuten"
    make -C "$BUILD_DIR/$name" clean >/dev/null 2>&1 || true
    make -C "$BUILD_DIR/$name" -j"$JOBS" >/dev/null
    install -m 755 "$BUILD_DIR/$name/$bin" "$target"
    ok "$name → $target"
}
if [ "${N8_SKIP_BUILD:-0}" = "1" ] && [ -x /usr/local/bin/MMDVMHost ] && [ -x /usr/local/bin/DMRGateway ]; then
    ok "übersprungen (N8_SKIP_BUILD=1)"
else
    systemctl stop mmdvmhost dmrgateway 2>/dev/null || true
    build MMDVMHost MMDVMHost "${MMDVMHOST_REF:-}" MMDVM-Host /usr/local/bin/MMDVMHost
    build DMRGateway DMRGateway "${DMRGATEWAY_REF:-}" DMRGateway /usr/local/bin/DMRGateway
    build MMDVMCal MMDVMCal "${MMDVMCAL_REF:-}" MMDVMCal /usr/local/bin/MMDVMCal
    mkdir -p /usr/local/share/DMRGateway
    cp -r "$BUILD_DIR/DMRGateway/Audio" /usr/local/share/DMRGateway/ 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
step "4/7 MQTT (mosquitto) nur lokal"
cat > /etc/mosquitto/conf.d/n8hotspot.conf <<'EOF'
# N8-Hotspot: MMDVMHost and DMRGateway publish their live data here (localhost only)
listener 1883 127.0.0.1
allow_anonymous true
EOF
systemctl enable -q mosquitto
systemctl restart mosquitto
ok "mosquitto auf 127.0.0.1:1883"

# ---------------------------------------------------------------------------
step "5/7 Weboberfläche nach ${N8_DIR}"
if [ "$SRC_DIR" != "$N8_DIR" ]; then
    mkdir -p "$N8_DIR"
    tar -C "$SRC_DIR" --exclude=./data --exclude=./venv --exclude=./.git -cf - . | tar -C "$N8_DIR" -xf -
    [ -d "$SRC_DIR/.git" ] && [ ! -d "$N8_DIR/.git" ] && cp -r "$SRC_DIR/.git" "$N8_DIR/"
fi
mkdir -p "$N8_DIR/data"
python3 -m venv "$N8_DIR/venv"
"$N8_DIR/venv/bin/pip" install -q --upgrade pip >/dev/null
"$N8_DIR/venv/bin/pip" install -q -r "$N8_DIR/requirements.txt"
chown -R "$SVC_USER:$SVC_USER" "$N8_DIR"
sudo -u "$SVC_USER" env N8HS_DATA="$N8_DIR/data" "$N8_DIR/venv/bin/python" -c \
    "import sys; sys.path.insert(0, '$N8_DIR'); from n8hotspot.__main__ import main; main(['', 'write-config'])" >/dev/null
ok "Python-Umgebung, Datenbank und Konfiguration in $N8_DIR/data"

# ---------------------------------------------------------------------------
step "6/7 Serielle Schnittstelle (Raspberry Pi)"
MODEL="$( { tr -d '\0' < /proc/device-tree/model; } 2>/dev/null || true)"
REBOOT=0
if [ "${N8_SKIP_UART:-0}" != "1" ] && [[ "$MODEL" == *Raspberry* ]]; then
    CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
    CMD=/boot/firmware/cmdline.txt; [ -f "$CMD" ] || CMD=/boot/cmdline.txt
    if ! grep -q '^# N8-Hotspot' "$CFG"; then
        printf '\n# N8-Hotspot: PL011-UART für das MMDVM-Modem (GPIO 14/15), Bluetooth aus\nenable_uart=1\ndtoverlay=disable-bt\n' >> "$CFG"
        REBOOT=1
    fi
    if grep -qE 'console=(serial0|ttyAMA0),[0-9]+ ?' "$CMD"; then
        sed -i -E 's/console=(serial0|ttyAMA0),[0-9]+ ?//g' "$CMD"
        REBOOT=1
    fi
    systemctl disable --now -q hciuart.service 2>/dev/null || true
    systemctl disable --now -q serial-getty@ttyAMA0.service serial-getty@serial0.service 2>/dev/null || true
    ok "$MODEL: /dev/ttyAMA0 frei für das Modem"
else
    ok "übersprungen (${MODEL:-kein Raspberry Pi})"
fi

# ---------------------------------------------------------------------------
step "7/7 Dienste"
for s in mmdvmhost dmrgateway n8hotspot; do
    install -m 644 "$N8_DIR/systemd/$s.service" "/etc/systemd/system/$s.service"
done
sed -i "s#/opt/n8hotspot#${N8_DIR}#g; s#N8HS_PORT=80#N8HS_PORT=${N8_PORT}#" /etc/systemd/system/{mmdvmhost,dmrgateway,n8hotspot}.service
SC=$(command -v systemctl)
cat > /etc/sudoers.d/n8hotspot <<EOF
# N8-Hotspot: the web interface may start/stop/restart its services and reboot
$SVC_USER ALL=(root) NOPASSWD: $SC start mmdvmhost.service, $SC stop mmdvmhost.service, $SC restart mmdvmhost.service, \\
    $SC start dmrgateway.service, $SC stop dmrgateway.service, $SC restart dmrgateway.service, \\
    $SC start mosquitto.service, $SC stop mosquitto.service, $SC restart mosquitto.service, \\
    $SC restart n8hotspot.service, $SC reboot, $SC poweroff
EOF
chmod 440 /etc/sudoers.d/n8hotspot
visudo -cq -f /etc/sudoers.d/n8hotspot || fail "sudoers-Regel fehlerhaft"
systemctl daemon-reload
systemctl enable -q dmrgateway mmdvmhost n8hotspot
systemctl restart dmrgateway mmdvmhost n8hotspot
ok "dmrgateway, mmdvmhost, n8hotspot gestartet und beim Booten aktiv"

[ "${N8_QUIET_END:-0}" = 1 ] && { [ "$REBOOT" = 1 ] && echo -e "   ${Y}Serielle Schnittstelle umgestellt: nach der Einrichtung einmal neu starten (sudo reboot).${N}"; exit 0; }
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
PORTSFX=""; [ "$N8_PORT" != "80" ] && PORTSFX=":$N8_PORT"
echo -e "
${G}━━ ✅ Fertig!${N}
   Weboberfläche:  ${B}http://$(hostname).local${PORTSFX}${N}  oder  ${B}http://${IP}${PORTSFX}${N}
   Login:          ${B}n8schicht${N} / ${B}n8schicht${N}  → bitte gleich ändern (Admin → My account)
   Danach:         Admin → Settings: Rufzeichen, DMR-ID, Frequenz, Passwort → Save → Restart now
"
[ "$REBOOT" = "1" ] && echo -e "   ${Y}Die serielle Schnittstelle wurde umgestellt: bitte einmal neu starten (sudo reboot).${N}\n"
exit 0
