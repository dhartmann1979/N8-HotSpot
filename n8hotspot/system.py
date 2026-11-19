"""System information and control of the services (systemctl via sudo)."""
from __future__ import annotations

import asyncio
import os
import platform
import shutil
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SERVICES = ("mmdvmhost", "dmrgateway", "mosquitto", "n8hotspot")
ACTIONS = ("start", "stop", "restart")
BIN = {"mmdvmhost": "/usr/local/bin/MMDVMHost", "dmrgateway": "/usr/local/bin/DMRGateway",
       "mmdvmcal": "/usr/local/bin/MMDVMCal"}


def _sudo() -> List[str]:
    return [] if os.geteuid() == 0 else ["sudo", "-n"]


async def run(cmd: List[str], timeout: float = 20) -> Dict[str, Any]:
    try:
        p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
        return {"rc": p.returncode, "out": out.decode("utf-8", "replace")}
    except FileNotFoundError:
        return {"rc": 127, "out": f"{cmd[0]}: not found"}
    except asyncio.TimeoutError:
        return {"rc": 124, "out": "timeout"}


class System:
    def __init__(self, demo: bool = False):
        self.demo = demo
        self.started = time.time()
        self._versions: Optional[Dict[str, str]] = None
        self._demo_state = {s: "active" for s in SERVICES}

    async def service_states(self) -> Dict[str, str]:
        if self.demo:
            return dict(self._demo_state)
        r = await run(["systemctl", "is-active", *SERVICES], 10)
        states = r["out"].split()
        return {s: (states[i] if i < len(states) else "unknown") for i, s in enumerate(SERVICES)}

    async def control(self, service: str, action: str) -> Dict[str, Any]:
        if service not in SERVICES or action not in ACTIONS:
            raise ValueError("unknown service or action")
        if self.demo:
            self._demo_state[service] = "inactive" if action == "stop" else "active"
            return {"rc": 0, "out": ""}
        return await run([*_sudo(), "systemctl", action, f"{service}.service"], 60)

    async def power(self, action: str) -> Dict[str, Any]:
        if action not in ("reboot", "poweroff"):
            raise ValueError("unknown action")
        if self.demo:
            return {"rc": 0, "out": ""}
        return await run([*_sudo(), "systemctl", action], 30)

    async def journal(self, service: str, lines: int = 200) -> str:
        if service not in SERVICES:
            raise ValueError("unknown service")
        if self.demo:
            return "(demo mode)"
        r = await run(["journalctl", "-u", f"{service}.service", "-n", str(min(int(lines), 2000)), "--no-pager", "-o", "short-iso"], 20)
        return r["out"]

    async def versions(self) -> Dict[str, str]:
        if self._versions is not None:
            return self._versions
        v: Dict[str, str] = {}
        if self.demo:
            v = {"mmdvmhost": "MMDVM-Host version 20261117 git #f030273", "dmrgateway": "DMRGateway version 20261102",
                 "mmdvmcal": "present"}
        else:
            for name in ("mmdvmhost", "dmrgateway"):
                path = BIN[name]
                if not Path(path).exists():
                    v[name] = "not installed"
                    continue
                r = await run([path, "-v"], 5)
                v[name] = (r["out"].strip().splitlines() or ["?"])[-1][:120]
            v["mmdvmcal"] = "present" if Path(BIN["mmdvmcal"]).exists() else "not installed"
        self._versions = v
        return v

    def info(self) -> Dict[str, Any]:
        def read(p: str, default: str = "") -> str:
            try:
                return Path(p).read_text().strip().strip("\x00")
            except Exception:
                return default
        temp = None
        t = read("/sys/class/thermal/thermal_zone0/temp")
        if t.isdigit():
            temp = round(int(t) / 1000, 1)
        mem = {}
        for line in read("/proc/meminfo").splitlines():
            k, _, v = line.partition(":")
            if k in ("MemTotal", "MemAvailable"):
                mem[k] = int(v.split()[0]) * 1024
        try:
            up = float(read("/proc/uptime", "0").split()[0])
        except ValueError:
            up = 0.0
        du = shutil.disk_usage("/")
        os_name = ""
        for line in read("/etc/os-release").splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"')
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
        info = {
            "hostname": socket.gethostname(), "model": read("/proc/device-tree/model") or platform.machine(),
            "os": os_name, "kernel": platform.release(), "python": platform.python_version(),
            "cpu_temp": temp, "load": [round(x, 2) for x in load], "cpus": os.cpu_count(),
            "mem_total": mem.get("MemTotal"), "mem_available": mem.get("MemAvailable"),
            "disk_total": du.total, "disk_free": du.free, "uptime": up, "ips": ips,
        }
        if self.demo:
            info.update({"hostname": "n8-hotspot", "model": "Raspberry Pi Zero 2 W Rev 1.0", "os": "Debian GNU/Linux 12 (bookworm)",
                         "cpu_temp": 47.2, "ips": ["192.168.178.57"], "cpus": 4, "load": [0.21, 0.18, 0.12],
                         "mem_total": 427 * 2 ** 20, "mem_available": 251 * 2 ** 20,
                         "disk_total": 29 * 2 ** 30, "disk_free": 26 * 2 ** 30, "uptime": 3 * 86400 + 4 * 3600})
        return info
