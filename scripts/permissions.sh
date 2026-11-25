#!/usr/bin/env bash
# N8-Hotspot – Berechtigungen prüfen und korrigieren (seit 1.5.0 über das gemeinsame N8 Admin-Kit)
#
#    sudo /opt/n8hotspot/scripts/permissions.sh            prüfen → korrigieren → erneut prüfen  (= n8-admin.sh fix-perms)
#    sudo /opt/n8hotspot/scripts/permissions.sh --check    nur prüfen                            (= n8-admin.sh check-perms)
#
# Geprüft werden Dienst-Benutzer und Gruppen (dialout = Modem), Programm (root, schreibgeschützt), Daten und Passwörter,
# systemd-Dienste, sudo, „Update jetzt“ und die Modem-Schnittstelle (Login-Konsole, UART) – siehe scripts/n8-admin.conf.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "${1:-}" = "--check" ] && exec "$HERE/n8-admin.sh" check-perms
exec "$HERE/n8-admin.sh" fix-perms
