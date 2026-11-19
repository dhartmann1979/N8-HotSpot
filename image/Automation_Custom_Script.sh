#!/bin/bash
# DietPi runs this once at the end of the first boot (AUTO_SETUP_CUSTOM_SCRIPT_EXEC=0).
# It installs N8-Hotspot from the copy that build-image.sh put on the boot
# partition, or from GitHub if that copy is missing.
LOG=/var/log/n8hotspot-firstboot.log
exec > >(tee -a "$LOG") 2>&1
echo "=== N8-Hotspot first boot: $(date) ==="

DEST=/opt/n8hotspot
for d in /boot /boot/firmware; do
    if [ -f "$d/n8hotspot.tar.gz" ]; then
        mkdir -p "$DEST"
        tar -C "$DEST" -xzf "$d/n8hotspot.tar.gz"
        echo "unpacked $d/n8hotspot.tar.gz"
        break
    fi
done
if [ ! -f "$DEST/scripts/install.sh" ]; then
    apt-get update -q && apt-get install -y -q git
    git clone --depth 1 https://github.com/dhartmann1979/N8-HotSpot "$DEST"
fi

N8_DIR="$DEST" bash "$DEST/scripts/install.sh"
rc=$?
echo "=== install.sh finished with $rc ==="
# hotspot settings from build-image.sh (contains the DMR password: read once, then delete)
for d in /boot /boot/firmware; do
    if [ $rc -eq 0 ] && [ -f "$d/n8hotspot-setup.json" ]; then
        install -m 600 -o n8hotspot "$d/n8hotspot-setup.json" /tmp/n8hotspot-setup.json
        (cd "$DEST" && sudo -u n8hotspot env N8HS_DATA="$DEST/data" ./venv/bin/python -m n8hotspot apply-setup /tmp/n8hotspot-setup.json)
        shred -u /tmp/n8hotspot-setup.json 2>/dev/null || rm -f /tmp/n8hotspot-setup.json
        rm -f "$d/n8hotspot-setup.json"
        echo "applied hotspot settings from $d/n8hotspot-setup.json"
    fi
done
# the serial port change needs a reboot; DietPi reboots after the first-run setup only if asked
if [ $rc -eq 0 ]; then
    ( sleep 20; systemctl reboot ) &
fi
exit 0
