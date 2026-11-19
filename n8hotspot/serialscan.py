"""
Find the modem: list serial ports and ask each free one for its MMDVM version.

Where MMDVM modems usually are:
  /dev/ttyAMA0      hat on the GPIO header of a Raspberry Pi (PL011 UART, Bluetooth off)
  /dev/serial0      alias of the GPIO UART
  /dev/ttyS0        GPIO UART when Bluetooth still owns ttyAMA0 (mini UART: unreliable)
  /dev/ttyACM0      ZUMspot, MMDVM_HS via USB, STM32 boards with native USB
  /dev/ttyUSB0      boards behind a USB-serial adapter (CH340, CP210x, FTDI)

Only the standard library is used (termios), so setup.sh can run it before the
Python environment exists. A port that is open in another program (normally
MMDVMHost) is not touched; its process is reported instead.
"""
from __future__ import annotations

import glob
import json
import os
import select
import termios
import time
from typing import Any, Dict, List, Optional

CANDIDATES = ("/dev/ttyAMA0", "/dev/serial0", "/dev/serial1", "/dev/ttyS0", "/dev/ttyAMA1")
SPEEDS = {115200: termios.B115200, 230400: getattr(termios, "B230400", termios.B115200),
          460800: getattr(termios, "B460800", termios.B115200)}
CPU = {0: "Atmel ARM", 1: "NXP ARM", 2: "ST-Micro ARM"}


def _sysfs_usb(name: str) -> Dict[str, str]:
    """USB vendor/product of /dev/ttyACMx or /dev/ttyUSBx from sysfs."""
    dev = os.path.realpath(f"/sys/class/tty/{name}/device")
    out: Dict[str, str] = {}
    try:
        out["driver"] = os.path.basename(os.path.realpath(os.path.join(dev, "driver")))
    except Exception:
        pass
    p = dev
    for _ in range(5):                      # walk up to the USB device
        p = os.path.dirname(p)
        if os.path.exists(os.path.join(p, "idVendor")):
            for k in ("idVendor", "idProduct", "manufacturer", "product", "serial"):
                try:
                    out[k] = open(os.path.join(p, k)).read().strip()
                except Exception:
                    pass
            break
    return out


def _users(path: str) -> List[Dict[str, Any]]:
    """Processes that have the device open (needs root or the same user)."""
    real = os.path.realpath(path)
    users = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                if os.path.realpath(f"/proc/{pid}/fd/{fd}") == real:
                    comm = open(f"/proc/{pid}/comm").read().strip()
                    users.append({"pid": int(pid), "name": comm})
                    break
        except Exception:
            continue
    return users


def _read_frame(fd: int, timeout: float) -> Optional[bytes]:
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], max(0.0, end - time.time()))
        if not r:
            break
        chunk = os.read(fd, 512)
        if not chunk:
            break
        buf += chunk
        i = buf.find(b"\xe0")
        if i >= 0 and len(buf) - i >= 2 and len(buf) - i >= buf[i + 1]:
            return buf[i:i + buf[i + 1]]
        j = buf.find(b"\xe1")
        if j >= 0 and len(buf) - j >= 3:
            n = (buf[j + 1] << 8) | buf[j + 2]
            if len(buf) - j >= n:
                return buf[j:j + n]
    return None


def parse_version(frame: bytes) -> Optional[Dict[str, Any]]:
    """MMDVM GET_VERSION answer -> protocol, description, CPU (same rules as MMDVMHost)."""
    if not frame or frame[0] not in (0xE0, 0xE1):
        return None
    off = 3 if frame[0] == 0xE1 else 2          # position of the type byte
    if len(frame) <= off + 1 or frame[off] != 0x00:
        return None
    proto = frame[off + 1]
    body = frame[off + 2:]
    if proto == 1:
        desc = body.split(b"\x00", 1)[0]
        return {"protocol": 1, "description": desc.decode("ascii", "replace").strip()}
    if proto == 2 and len(body) >= 19:
        return {"protocol": 2, "cpu": CPU.get(body[2], "unknown"),
                "description": body[19:].split(b"\x00", 1)[0].decode("ascii", "replace").strip()}
    return {"protocol": proto, "description": ""}


def probe(path: str, speed: int = 115200, wait: float = 1.2) -> Optional[Dict[str, Any]]:
    """Open the port, send GET_VERSION (E0 03 00), return the parsed answer or None."""
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        attrs = termios.tcgetattr(fd)
        attrs[0] = 0                                     # iflag
        attrs[1] = 0                                     # oflag
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0                                     # lflag
        attrs[4] = attrs[5] = SPEEDS.get(speed, termios.B115200)
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        termios.tcflush(fd, termios.TCIOFLUSH)
        time.sleep(0.3)
        for _ in range(3):
            os.write(fd, b"\xe0\x03\x00")
            frame = _read_frame(fd, wait)
            info = parse_version(frame) if frame else None
            if info:
                return info
        return None
    finally:
        os.close(fd)


def list_ports() -> List[str]:
    found = []
    for p in list(CANDIDATES) + sorted(glob.glob("/dev/ttyACM*")) + sorted(glob.glob("/dev/ttyUSB*")):
        if os.path.exists(p) and p not in found:
            found.append(p)
    return found


def scan(speeds=(115200, 460800), do_probe: bool = True) -> List[Dict[str, Any]]:
    """Every serial port with what is known about it."""
    out = []
    seen_real = {}
    for p in list_ports():
        real = os.path.realpath(p)
        name = os.path.basename(real)
        entry: Dict[str, Any] = {"port": p, "real": real if real != p else "", "kind": "", "usb": {}, "users": [],
                                 "status": "unknown", "modem": None, "speed": None}
        if name.startswith("ttyACM") or name.startswith("ttyUSB"):
            entry["kind"] = "usb"
            entry["usb"] = _sysfs_usb(name)
        elif name in ("ttyAMA0", "ttyAMA1"):
            entry["kind"] = "gpio"
        elif name == "ttyS0":
            entry["kind"] = "gpio-mini"
        else:
            entry["kind"] = "other"
        if real in seen_real:                            # alias such as /dev/serial0 -> ttyAMA0
            entry.update(status="alias", alias_of=seen_real[real])
            out.append(entry)
            continue
        seen_real[real] = p
        entry["users"] = _users(p)
        if entry["users"]:
            entry["status"] = "busy"
        elif do_probe:
            try:
                for sp in speeds:
                    info = probe(p, sp)
                    if info:
                        entry.update(status="modem", modem=info, speed=sp)
                        break
                else:
                    entry["status"] = "silent"
            except PermissionError:
                entry["status"] = "no-permission"
            except OSError as e:
                entry.update(status="error", error=str(e))
        out.append(entry)
    return out


if __name__ == "__main__":
    print(json.dumps(scan(), indent=1))
