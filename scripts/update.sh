#!/usr/bin/env bash
# N8-Hotspot aktualisieren:   sudo /opt/n8hotspot/scripts/update.sh
# Mit neuem MMDVMHost/DMRGateway/MMDVMCal:   sudo /opt/n8hotspot/scripts/update.sh --rebuild
#
# Seit 1.5.0 über das gemeinsame N8 Admin-Kit (wie „Update jetzt“ im Browser): nur vorspulen (bricht bei von Hand
# geänderten Dateien ab), Python-Pakete, Dienste und ini-Dateien, Berechtigungen und sudo, Neustart, Prüfung der
# Weboberfläche – antwortet sie nicht, geht es automatisch zurück auf den alten Stand.
set -euo pipefail
N8_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo starten."; exit 1; }
if [ "${1:-}" = "--rebuild" ]; then
    "$N8_DIR/scripts/n8-admin.sh" update
    N8_DIR="$N8_DIR" N8_SKIP_UART=1 "$N8_DIR/scripts/install.sh"
    exit 0
fi
exec "$N8_DIR/scripts/n8-admin.sh" update
