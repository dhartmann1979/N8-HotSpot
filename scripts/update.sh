#!/usr/bin/env bash
# N8-Hotspot aktualisieren:   sudo /opt/n8hotspot/scripts/update.sh
# Mit neuem MMDVMHost/DMRGateway/MMDVMCal:   sudo /opt/n8hotspot/scripts/update.sh --rebuild
set -euo pipefail
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
chown -R n8hotspot:n8hotspot "$N8_DIR"
systemctl restart n8hotspot
echo "✅ N8-Hotspot aktualisiert ($(git -C "$N8_DIR" log -1 --format='%h %ad' --date=short 2>/dev/null || echo ok))."
