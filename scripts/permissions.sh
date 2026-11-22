#!/usr/bin/env bash
# =============================================================================
#  N8-Hotspot – Berechtigungen prüfen und reparieren (als root)
#
#    sudo /opt/n8hotspot/scripts/permissions.sh            prüfen und reparieren
#    sudo /opt/n8hotspot/scripts/permissions.sh --check    nur prüfen, nichts ändern
#
#  Wird auch von install.sh und update.sh aufgerufen. Repariert:
#    - Gruppen des Dienst-Benutzers (dialout = Zugriff auf das Modem, systemd-journal = Logs)
#    - systemd-Dienste (Port der Weboberfläche bleibt erhalten)
#    - sudo-Regel /etc/sudoers.d/n8hotspot (nur Start/Stopp/Neustart der eigenen Dienste)
#    - Besitzer des Programmordners (für „Update now“ im Browser)
#    - serielle Konsole / getty auf der Modem-Schnittstelle (Raspberry Pi)
# =============================================================================
set -uo pipefail

N8_DIR="${N8_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SVC_USER="${SVC_USER:-n8hotspot}"
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
CHANGED=0; PROBLEMS=0; N8_REBOOT="${N8_REBOOT:-0}"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
good() { echo -e "   ${G}✓${N} $*"; }
fixd() { echo -e "   ${Y}↻${N} $*"; CHANGED=1; }
bad()  { echo -e "   ${R}✗${N} $*"; PROBLEMS=1; }

[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo starten: sudo $0"; exit 1; }
id "$SVC_USER" >/dev/null 2>&1 || { bad "Benutzer $SVC_USER fehlt – bitte scripts/install.sh ausführen"; exit 1; }
SC=$(command -v systemctl)

# --- groups -----------------------------------------------------------------
for g in dialout systemd-journal adm gpio i2c spi; do
    getent group "$g" >/dev/null || continue
    if id -nG "$SVC_USER" | tr ' ' '\n' | grep -qx "$g"; then
        [ "$g" = dialout ] && good "$SVC_USER ist in der Gruppe dialout (Modem)"
    elif [ $CHECK = 1 ]; then bad "$SVC_USER fehlt in der Gruppe $g"
    else usermod -aG "$g" "$SVC_USER"; fixd "$SVC_USER zur Gruppe $g hinzugefügt"; fi
done

# --- serial devices ---------------------------------------------------------
# GPIO UART (and whatever /dev/serial0 points to) plus USB modems; an unused mini UART is not reported
PORTS=""
for p in /dev/ttyAMA0 "$(readlink -f /dev/serial0 2>/dev/null)" /dev/ttyACM* /dev/ttyUSB*; do
    [ -n "$p" ] && [ -e "$p" ] && [[ " $PORTS " != *" $p "* ]] && PORTS="$PORTS $p"
done
for p in $PORTS; do
    if sudo -u "$SVC_USER" test -r "$p" -a -w "$p"; then good "$SVC_USER darf $p öffnen ($(stat -c '%G %A' "$p"))"
    else
        grp=$(stat -c %G "$p")
        if [ "$grp" = tty ] && [ $CHECK = 0 ]; then
            # a login console (getty) owns the port – free it for the modem
            n=$(basename "$p")
            systemctl disable --now -q "serial-getty@$n.service" 2>/dev/null || true
            fixd "Login-Konsole auf $p abgeschaltet (Gruppe war tty)"
        else
            bad "$SVC_USER darf $p nicht öffnen (Gruppe $grp, $(stat -c %A "$p"))"
        fi
    fi
done
MODEL="$( { tr -d '\0' < /proc/device-tree/model; } 2>/dev/null || true)"
if [[ "$MODEL" == *Raspberry* ]] && [ "${N8_SKIP_UART:-0}" != 1 ]; then
    CMD=/boot/firmware/cmdline.txt; [ -f "$CMD" ] || CMD=/boot/cmdline.txt
    if [ -f "$CMD" ] && grep -qE 'console=(serial0|ttyAMA0|ttyS0),[0-9]+ ?' "$CMD"; then
        if [ $CHECK = 1 ]; then bad "Linux-Konsole läuft auf der Modem-Schnittstelle ($CMD)"
        else sed -i -E 's/console=(serial0|ttyAMA0|ttyS0),[0-9]+ ?//g' "$CMD"; fixd "Linux-Konsole von der Modem-Schnittstelle genommen – Neustart nötig"; N8_REBOOT=1; fi
    fi
    if [ "$(readlink -f /dev/serial0 2>/dev/null)" = /dev/ttyS0 ] && [ -e /dev/ttyAMA0 ]; then
        bad "/dev/serial0 zeigt auf den Mini-UART (Bluetooth aktiv). In config.txt fehlt dtoverlay=disable-bt – scripts/install.sh setzt es, danach Neustart"
    fi
fi

# --- systemd units ----------------------------------------------------------
PORT=$(sed -n 's/^Environment=N8HS_PORT=//p' /etc/systemd/system/n8hotspot.service 2>/dev/null | head -1)
PORT="${PORT:-${N8_PORT:-80}}"
for s in mmdvmhost dmrgateway n8hotspot; do
    want=$(sed "s#/opt/n8hotspot#${N8_DIR}#g; s#N8HS_PORT=80#N8HS_PORT=${PORT}#" "$N8_DIR/systemd/$s.service")
    if [ "$want" = "$(cat "/etc/systemd/system/$s.service" 2>/dev/null)" ]; then good "Dienst $s.service aktuell"
    elif [ $CHECK = 1 ]; then bad "Dienst $s.service weicht von der Vorlage ab"
    else printf '%s\n' "$want" > "/etc/systemd/system/$s.service"; chmod 644 "/etc/systemd/system/$s.service"
         fixd "Dienst $s.service erneuert"; UNITS=1; fi
done
[ "${UNITS:-0}" = 1 ] && systemctl daemon-reload

# --- sudo rule --------------------------------------------------------------
RULE="# N8-Hotspot: the web interface may start/stop/restart its services and reboot (scripts/permissions.sh)
$SVC_USER ALL=(root) NOPASSWD: $SC start mmdvmhost.service, $SC stop mmdvmhost.service, $SC restart mmdvmhost.service, \\
    $SC start dmrgateway.service, $SC stop dmrgateway.service, $SC restart dmrgateway.service, \\
    $SC start mosquitto.service, $SC stop mosquitto.service, $SC restart mosquitto.service, \\
    $SC restart n8hotspot.service, $SC reboot, $SC poweroff"
if [ "$RULE" = "$(cat /etc/sudoers.d/n8hotspot 2>/dev/null)" ]; then good "sudo-Regel /etc/sudoers.d/n8hotspot aktuell"
elif [ $CHECK = 1 ]; then bad "sudo-Regel fehlt oder ist veraltet"
else
    tmp=$(mktemp); printf '%s\n' "$RULE" > "$tmp"
    if visudo -cq -f "$tmp"; then install -m 440 -o root -g root "$tmp" /etc/sudoers.d/n8hotspot; fixd "sudo-Regel neu geschrieben"
    else bad "sudo-Regel fehlerhaft – nicht übernommen"; fi
    rm -f "$tmp"
fi

# --- ownership (git, venv, data) ---------------------------------------------
wrong=$(find "$N8_DIR" -xdev ! -user "$SVC_USER" -print -quit 2>/dev/null)
if [ -z "$wrong" ]; then good "$N8_DIR gehört $SVC_USER (Update im Browser möglich)"
elif [ $CHECK = 1 ]; then bad "$wrong gehört nicht $SVC_USER"
else chown -R "$SVC_USER:$SVC_USER" "$N8_DIR"; fixd "Besitzer von $N8_DIR auf $SVC_USER gesetzt"; fi

export N8_REBOOT
if [ $CHECK = 1 ]; then [ $PROBLEMS = 0 ] && echo -e "   ${G}Alles in Ordnung.${N}" || echo -e "   ${Y}Reparieren mit: sudo $N8_DIR/scripts/permissions.sh${N}"; fi
# Run on its own: restart what was changed (install.sh/update.sh set N8_NO_RESTART=1 and restart themselves)
if [ $CHECK = 0 ] && [ $CHANGED = 1 ] && [ "${N8_NO_RESTART:-0}" != 1 ]; then
    systemctl restart dmrgateway mmdvmhost n8hotspot 2>/dev/null || true
    echo -e "   Dienste neu gestartet."
fi
[ "$N8_REBOOT" = 1 ] && echo -e "   ${Y}Bitte einmal neu starten: sudo reboot${N}"
[ $PROBLEMS = 0 ]
