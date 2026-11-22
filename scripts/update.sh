#!/usr/bin/env bash
# N8-Hotspot aktualisieren:   sudo /opt/n8hotspot/scripts/update.sh
# Mit neuem MMDVMHost/DMRGateway/MMDVMCal:   sudo /opt/n8hotspot/scripts/update.sh --rebuild
#
# Ablauf: git pull, Python-Pakete, Berechtigungen prüfen und reparieren (scripts/permissions.sh), Dienste neu starten.
# Alles steht in main(): bash liest so das ganze Skript ein, bevor git pull es eventuell ersetzt.
set -euo pipefail

main() {
    local N8_DIR
    N8_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    [ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo starten."; exit 1; }
    if [ -d "$N8_DIR/.git" ]; then
        git config --global --add safe.directory "$N8_DIR" 2>/dev/null || true
        git -C "$N8_DIR" pull --ff-only
    fi
    if [ "${1:-}" = "--rebuild" ]; then
        N8_DIR="$N8_DIR" "$N8_DIR/scripts/install.sh"
        exit 0
    fi
    "$N8_DIR/venv/bin/pip" install -q -r "$N8_DIR/requirements.txt"
    # Gruppe dialout (Modem-Scan), Dienste, sudo-Regel, Besitzer – die neue Version des Skripts nach dem pull
    echo "🔐 Berechtigungen:"
    N8_DIR="$N8_DIR" N8_NO_RESTART=1 bash "$N8_DIR/scripts/permissions.sh" || echo "   ⚠️  Nicht alles ließ sich reparieren – siehe oben."
    systemctl restart dmrgateway mmdvmhost n8hotspot
    echo "✅ N8-Hotspot aktualisiert ($(git -C "$N8_DIR" log -1 --format='%h %ad' --date=short 2>/dev/null || echo ok))."
    exit 0
}
main "$@"
