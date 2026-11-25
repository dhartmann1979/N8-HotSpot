"""
Can the running web interface reach the modem? Shown in the modem scan and in Admin → System.

Everything here only reads, from the point of view of the running process (groups count only after a restart).
Program folder, data, units and sudo are checked by the N8 Admin-Kit (scripts/n8-admin.sh check-perms);
repairs need root: scripts/n8-admin.sh fix-perms (also run by install.sh and every update).
"""
from __future__ import annotations

import grp
import os
from typing import Any, Dict, List

from . import serialscan, updater

def fix_command() -> str:
    return f"sudo {updater.REPO_ROOT}/scripts/n8-admin.sh fix-perms"


def _item(key: str, label: str, ok: bool, detail: str = "", level: str = "bad") -> Dict[str, Any]:
    return {"key": key, "label": label, "ok": ok, "detail": detail, "level": "ok" if ok else level}


def ports_to_check(configured: str = "") -> List[str]:
    """GPIO UART, whatever /dev/serial0 points to, USB modems and the configured port (an idle mini UART is skipped)."""
    out: List[str] = []
    for p in ["/dev/ttyAMA0", os.path.realpath("/dev/serial0") if os.path.exists("/dev/serial0") else "",
              configured, *[x for x in serialscan.list_ports() if "ttyACM" in x or "ttyUSB" in x]]:
        if p and os.path.exists(p):
            real = os.path.realpath(p)
            if real not in out:
                out.append(real)
    return out


def check(configured_port: str = "") -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    # 1) group dialout of the running process (a usermod only counts after a restart of the service)
    try:
        gid = grp.getgrnam("dialout").gr_gid
        in_dialout = os.geteuid() == 0 or gid in os.getgroups() or os.getegid() == gid
    except KeyError:
        in_dialout = True
    items.append(_item("dialout", "Web interface is in the group dialout (modem scan, calibration)", in_dialout,
                       "" if in_dialout else "The service runs without the group dialout – the scan cannot open the serial ports."))
    # 2) every relevant serial port can be opened
    for p in ports_to_check(configured_port):
        ok = os.access(p, os.R_OK | os.W_OK)
        try:
            st = os.stat(p)
            owner = f"group {grp.getgrgid(st.st_gid).gr_name}, mode {oct(st.st_mode & 0o777)[2:]}"
        except (OSError, KeyError):
            owner = ""
        items.append(_item("port:" + p, f"Serial port {p} can be opened", ok,
                           owner if ok else f"No access ({owner}). A login console (group tty) or a missing group dialout is the usual cause."))
    if configured_port and not os.path.exists(configured_port):
        items.append(_item("port-missing", f"Configured modem port {configured_port} exists", False,
                           "The port does not exist – use the modem scan to find the right one.", "warn"))
    # 3) Linux console on the modem UART (Raspberry Pi)
    try:
        cmdline = open("/proc/cmdline").read()
    except OSError:
        cmdline = ""
    console = any(f"console={x}," in cmdline for x in ("serial0", "ttyAMA0", "ttyS0"))
    items.append(_item("console", "No Linux console on the modem UART", not console,
                       "console=serial0/ttyAMA0 is in the kernel command line – the modem gets garbage. Fix, then reboot." if console else ""))
    if os.path.exists("/dev/serial0") and os.path.realpath("/dev/serial0") == "/dev/ttyS0" and os.path.exists("/dev/ttyAMA0"):
        items.append(_item("bt", "GPIO UART is the full PL011 (Bluetooth off)", False,
                           "/dev/serial0 points to the mini UART. Add dtoverlay=disable-bt to config.txt (install.sh does it) and reboot.", "warn"))
    bad = [i for i in items if not i["ok"]]
    return {"ok": not bad, "items": items, "problems": len(bad), "fix": fix_command(),
            "critical": any(i["level"] == "bad" for i in bad)}
