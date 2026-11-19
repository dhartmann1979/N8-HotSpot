"""
Modem calibration with MMDVMCal (g4klx), driven from the browser.

MMDVMCal needs the serial port, so MMDVMHost and DMRGateway are stopped while
it runs and started again afterwards. It reads single key presses from a
terminal, therefore it runs in a pseudo terminal (pty).

Typical hotspot calibration (simplex, MMDVM_HS boards):
  1. enter the RX frequency (E), switch to "BER Test Mode (FEC) for DMR Simplex" (b)
  2. transmit with a radio on that frequency (CC1, any TG)
  3. move the frequency up/down (F/f) until the BER is lowest
  4. offset = found frequency - nominal frequency -> RX and TX offset
"""
from __future__ import annotations

import asyncio
import os
import pty
import re
import signal
import subprocess
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

KEYS = {   # what the buttons may send (HS boards)
    "b": "BER test DMR simplex (FEC)", "B": "BER test DMR 1031 Hz pattern", "D": "DMR deviation mode",
    "M": "DMR simplex 1031 Hz test pattern", "S": "RSSI mode", "C": "Carrier only", " ": "Toggle transmit",
    "F": "Frequency up", "f": "Frequency down", "T": "Deviation up", "t": "Deviation down",
    "P": "RF power up", "p": "RF power down", "H": "Help", "V": "Version",
}

RE_FREQ = re.compile(r"(?:TX frequency|New frequency):\s*(\d+)")
RE_STEP = re.compile(r"New frequency step:\s*(\d+)")
RE_BER = re.compile(r"DMR audio seq\. \d+, (?:FEC|1031 Test Pattern) BER % \(errs\): ([\d.]+)%")
RE_BER_END = re.compile(r"DMR voice end received, total frames: \d+, bits: \d+, errors: \d+, BER: ([\d.]+)%")
RE_MODE = re.compile(r"^(BER Test Mode.*|DMR Deviation Mode.*|DMR Simplex 1031 Hz Test Pattern.*|RSSI Mode|Carrier Only Mode.*|DMR Duplex 1031.*)$")
RE_TX = re.compile(r"Set transmitter (ON|OFF)")
RE_LEVEL = re.compile(r"(TX Level|RF power): ([\d.]+)%")
RE_RSSI = re.compile(r"RSSI: max: (\d+), min: (\d+), ave: (\d+)")


class CalSession:
    def __init__(self, binary: str, emit: Callable[[Dict[str, Any]], None]):
        self.binary = binary
        self.emit = emit
        self.proc: Optional[subprocess.Popen] = None
        self.fd: Optional[int] = None
        self.buf = ""
        self.lines: Deque[str] = deque(maxlen=400)
        self.state: Dict[str, Any] = {}
        self.reset_state()

    def reset_state(self, nominal: int = 0) -> None:
        self.state = {"running": False, "nominal": nominal, "freq": nominal, "step": 50, "mode": "", "tx": False,
                      "ber": None, "ber_end": None, "ber_hist": [], "best": None, "started": None, "rssi": None,
                      "tx_level": None, "power": None}

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def snapshot(self) -> Dict[str, Any]:
        s = dict(self.state)
        s["running"] = self.running
        s["offset"] = (s["freq"] - s["nominal"]) if s["nominal"] else None
        s["lines"] = list(self.lines)[-120:]
        return s

    async def start(self, port: str, speed: int, nominal: int) -> None:
        if self.running:
            raise RuntimeError("Calibration is already running.")
        if not os.path.exists(self.binary.split()[0]):
            raise RuntimeError(f"{self.binary} is not installed.")
        self.reset_state(nominal)
        self.lines.clear()
        master, slave = pty.openpty()
        cmd = self.binary.split() + [str(speed), port]
        self.proc = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave, close_fds=True,
                                     start_new_session=True)
        os.close(slave)
        self.fd = master
        self.state.update(running=True, started=time.time())
        loop = asyncio.get_running_loop()
        loop.add_reader(master, self._read)
        await asyncio.sleep(2.6)            # MMDVMCal waits 2 s for the modem
        if nominal:
            await self.enter_freq(nominal)
        self.emit({"type": "cal", "cal": self.snapshot()})

    def _read(self) -> None:
        try:
            data = os.read(self.fd, 4096)
        except OSError:
            data = b""
        if not data:
            self._closed()
            return
        self.buf += data.decode("utf-8", "replace").replace("\r", "")
        *done, self.buf = self.buf.split("\n")
        changed = False
        for line in done:
            line = line.rstrip()
            if not line:
                continue
            self.lines.append(line)
            changed = self._parse(line) or changed
            self.emit({"type": "cal_line", "line": line})
        if changed:
            self.emit({"type": "cal", "cal": self.snapshot()})

    def _parse(self, line: str) -> bool:
        s = self.state
        m = RE_FREQ.search(line)
        if m:
            s["freq"] = int(m.group(1))
            s["ber_hist"] = []
            return True
        m = RE_STEP.search(line)
        if m:
            s["step"] = int(m.group(1))
            return True
        m = RE_BER.search(line)
        if m:
            ber = float(m.group(1))
            s["ber"] = ber
            s["ber_hist"] = (s["ber_hist"] + [ber])[-40:]
            return True
        m = RE_BER_END.search(line)
        if m:
            ber = float(m.group(1))
            s["ber_end"] = ber
            if s["best"] is None or ber < s["best"]["ber"]:
                s["best"] = {"freq": s["freq"], "ber": ber, "offset": s["freq"] - s["nominal"] if s["nominal"] else None}
            return True
        m = RE_TX.search(line)
        if m:
            s["tx"] = m.group(1) == "ON"
            return True
        m = RE_LEVEL.search(line)
        if m:
            s["tx_level" if m.group(1) == "TX Level" else "power"] = float(m.group(2))
            return True
        m = RE_RSSI.search(line)
        if m:
            s["rssi"] = {"max": int(m.group(1)), "min": int(m.group(2)), "ave": int(m.group(3))}
            return True
        m = RE_MODE.match(line.strip())
        if m:
            s["mode"] = m.group(1)
            return True
        return False

    def _closed(self) -> None:
        if self.fd is not None:
            try:
                asyncio.get_running_loop().remove_reader(self.fd)
            except Exception:
                pass
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd = None
        self.state["running"] = False
        self.emit({"type": "cal", "cal": self.snapshot()})

    def _write(self, text: str) -> None:
        if not self.running or self.fd is None:
            raise RuntimeError("Calibration is not running.")
        os.write(self.fd, text.encode())

    async def key(self, key: str) -> None:
        if key not in KEYS:
            raise ValueError("unknown key")
        self._write(key)

    async def enter_freq(self, hz: int) -> None:
        if not 100_000_000 <= int(hz) <= 1_000_000_000:
            raise ValueError("frequency out of range")
        self._write("E")
        await asyncio.sleep(0.3)
        self._write(f"{int(hz)}\n")
        self.state["ber_hist"] = []

    async def set_step(self, hz: int) -> None:
        if not 1 <= int(hz) <= 100_000:
            raise ValueError("step out of range")
        self._write("Z")
        await asyncio.sleep(0.3)
        self._write(f"{int(hz)}\n")

    async def stop(self) -> None:
        if self.running:
            try:
                if self.state.get("tx"):
                    self._write(" ")
                    await asyncio.sleep(0.3)
                self._write("q")
            except Exception:
                pass
            for _ in range(30):
                if self.proc.poll() is not None:
                    break
                await asyncio.sleep(0.1)
            if self.proc.poll() is None:
                os.killpg(self.proc.pid, signal.SIGTERM)
                await asyncio.sleep(0.5)
        if self.fd is not None:
            self._closed()
        self.proc = None
