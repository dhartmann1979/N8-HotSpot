"""
Live data from MMDVMHost and DMRGateway via MQTT (mosquitto on localhost).

MMDVMHost publishes JSON on ``mmdvm/json`` (calls, mode, modem, BER, RSSI) and
log lines on ``mmdvm/log``; DMRGateway publishes ``dmr-gateway/json``
(connection to the DMR server) and ``dmr-gateway/log``.
Every finished call is stored in SQLite (table ``calls``).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from .db import DB

log = logging.getLogger("n8hotspot.live")

LOG_RE = re.compile(r"^([A-Z?]): (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) (.*)$")
LEVELS = {"D": "debug", "M": "message", "I": "info", "W": "warning", "E": "error", "F": "fatal", "?": "info"}


class Live:
    def __init__(self, db: DB, lookup: Callable[[int], Dict[str, str]]):
        self.db = db
        self.lookup = lookup
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.listeners: List[Callable[[Dict[str, Any]], Any]] = []
        self.mqtt_connected = False
        self.modem: Dict[str, Any] = {"open": None}
        self.mode = "Idle"
        self.link: Dict[str, Any] = {"state": "unknown", "network": "", "reason": "", "since": None, "message": ""}
        self.slots: Dict[int, Optional[Dict[str, Any]]] = {1: None, 2: None}
        self.last_mmdvm = 0.0
        self.last_gateway = 0.0
        self.logs: Deque[Dict[str, Any]] = deque(maxlen=500)
        self.last_heard: List[Dict[str, Any]] = []
        self._client = None
        self._load_last_heard()

    # ------------------------------------------------------------ plumbing
    def emit(self, event: Dict[str, Any]) -> None:
        for fn in list(self.listeners):
            try:
                r = fn(event)
                if asyncio.iscoroutine(r):
                    asyncio.ensure_future(r)
            except Exception:
                log.exception("listener failed")

    def _load_last_heard(self) -> None:
        rows = self.db.q("SELECT * FROM calls ORDER BY ts DESC LIMIT 40")
        self.last_heard = [self._row(r) for r in rows]

    def _row(self, r) -> Dict[str, Any]:
        d = dict(r)
        d["group"] = bool(d.pop("grp"))
        d["is_data"] = bool(d["is_data"])
        d.update({k: v for k, v in self.lookup(d.get("src_id") or 0).items() if k in ("name", "city", "country")})
        if not d.get("callsign") and d.get("src_id"):
            d["callsign"] = self.lookup(d["src_id"]).get("callsign", "")
        return d

    def snapshot(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "mqtt": self.mqtt_connected, "modem": self.modem, "mode": self.mode, "link": self.link,
            "slots": {str(k): v for k, v in self.slots.items()},
            "mmdvm_seen": self.last_mmdvm, "gateway_seen": self.last_gateway, "now": now,
            "last_heard": self.last_heard[:30],
        }

    # ------------------------------------------------------------ MQTT
    def start_mqtt(self, loop: asyncio.AbstractEventLoop, host: str = "127.0.0.1", port: int = 1883) -> None:
        self.loop = loop
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            log.error("paho-mqtt is missing: pip install paho-mqtt")
            return
        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"n8hotspot-{int(time.time())}")
        except AttributeError:      # paho-mqtt 1.x
            c = mqtt.Client(client_id=f"n8hotspot-{int(time.time())}")

        def on_connect(client, userdata, flags, rc, properties=None):
            self._threadsafe(self._set_mqtt, True)
            client.subscribe([("mmdvm/#", 0), ("dmr-gateway/#", 0)])

        def on_disconnect(client, userdata, *args):
            self._threadsafe(self._set_mqtt, False)

        def on_message(client, userdata, msg):
            self._threadsafe(self.handle, msg.topic, msg.payload)

        c.on_connect, c.on_disconnect, c.on_message = on_connect, on_disconnect, on_message
        c.reconnect_delay_set(1, 10)
        self._client = c

        def run():
            while True:
                try:
                    c.connect(host, port, 30)
                    c.loop_forever(retry_first_connection=True)
                except Exception as e:
                    log.warning(f"MQTT {host}:{port} not reachable ({e}); retrying")
                    time.sleep(5)
        threading.Thread(target=run, name="mqtt", daemon=True).start()

    def _threadsafe(self, fn, *args) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(fn, *args)
        else:
            fn(*args)

    def _set_mqtt(self, ok: bool) -> None:
        self.mqtt_connected = ok
        self.emit({"type": "status", "status": self.snapshot()})

    # ------------------------------------------------------------ parsing
    def handle(self, topic: str, payload) -> None:
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8", "replace")
        app = "gateway" if topic.startswith("dmr-gateway") else "mmdvm"
        now = time.time()
        if app == "gateway":
            self.last_gateway = now
        else:
            self.last_mmdvm = now
        if topic.endswith("/log"):
            self._log(app, payload)
            return
        if not topic.endswith("/json"):
            return
        try:
            data = json.loads(payload)
        except ValueError:
            return
        if not isinstance(data, dict):
            return
        for kind, body in data.items():
            if not isinstance(body, dict):
                continue
            try:
                self._json(app, kind, body)
            except Exception:
                log.exception(f"bad {kind} message: {body}")

    def _log(self, app: str, line: str) -> None:
        line = line.strip()
        m = LOG_RE.match(line)
        level, text = (LEVELS.get(m.group(1), "info"), m.group(3)) if m else ("info", line)
        entry = {"ts": time.time(), "app": app, "level": level, "text": text}
        self.logs.append(entry)
        self.emit({"type": "log", "entry": entry})
        if app == "gateway":
            if "Logged into the master successfully" in text or "Logged into the master via DTC" in text:
                self._set_link("connected", text.split(",")[0], "", text)
            elif "timed out" in text or "Login to the master has failed" in text:
                self._set_link("failed", text.split(",")[0], "timeout" if "timed out" in text else "login", text)

    def _set_link(self, state: str, network: str = "", reason: str = "", message: str = "") -> None:
        if self.link.get("state") != state:
            self.link["since"] = time.time()
        self.link.update({"state": state, "network": network or self.link.get("network", ""),
                          "reason": reason, "message": message})
        self.emit({"type": "status", "status": self.snapshot()})

    def _json(self, app: str, kind: str, b: Dict[str, Any]) -> None:
        if app == "gateway":
            if kind == "status":
                msg = str(b.get("message", ""))
                name = msg.split(": ", 1)[1] if ": " in msg else ""
                if msg.startswith("Logged into"):
                    self._set_link("connected", name, "", msg)
                elif msg.startswith(("Failed", "Connection closing")):
                    self._set_link("failed", name, self.link.get("reason", ""), msg)
                elif msg.startswith("Opening"):
                    if self.link.get("state") == "failed" and self.link.get("reason"):
                        self.link["message"] = "Retrying …"     # keep showing why it failed
                        self.emit({"type": "status", "status": self.snapshot()})
                    else:
                        self._set_link("connecting", name, "", msg)
            elif kind == "link" and b.get("action") in ("linking", "unlinked") and not str(b.get("network", "")).startswith("XLX"):
                if b["action"] == "linking":
                    self._set_link("connected", str(b.get("network", "")), "", "Linked")
                else:
                    self._set_link("failed", str(b.get("network", "")), "disconnected", "Not linked")
            elif kind == "link" and b.get("action") == "failed":
                self._set_link("failed", str(b.get("network", "")), str(b.get("reason", "")),
                               f"Connection failed: {b.get('reason', '')}")
            return
        if kind == "MMDVM":
            if "mode" in b:
                m = str(b["mode"])
                self.mode = {"idle": "Idle", "dmr": "DMR", "lockout": "Lockout", "error": "Error", "quit": "Stopped"}.get(m.lower(), m)
                self.emit({"type": "status", "status": self.snapshot()})
            return
        if kind == "Modem":
            self.modem = b
            self.emit({"type": "status", "status": self.snapshot()})
            return
        if kind in ("BER", "RSSI") and b.get("mode") == "DMR":
            call = self.slots.get(int(b.get("slot", 0)))
            if call:
                call["ber_live" if kind == "BER" else "rssi_live"] = b.get("value")
                self.emit({"type": "slot", "slot": int(b["slot"]), "call": call})
            return
        if kind != "DMR":
            return
        action, slot = b.get("action"), int(b.get("slot", 0) or 0)
        if slot not in (1, 2):
            return
        if action in ("start", "late_entry"):
            cur = self.slots.get(slot)
            if cur and (cur["src_id"] != b.get("src_id") or cur["dst_id"] != b.get("dst_id")):
                self._finish(slot, {"action": "lost"})
            if self.slots.get(slot):
                return
            src_id = int(b.get("src_id") or 0)
            info = self.lookup(src_id)
            src_info = str(b.get("src_info") or "").strip()
            callsign = src_info if src_info and not src_info.isdigit() else info.get("callsign", "")
            self.slots[slot] = {
                "slot": slot, "source": b.get("source", "rf"), "src_id": src_id, "callsign": callsign,
                "name": info.get("name", ""), "city": info.get("city", ""), "country": info.get("country", ""),
                "dst_id": int(b.get("dst_id") or 0), "group": b.get("group", "yes") == "yes",
                "is_data": "frames" in b, "start": time.time(),
            }
            self.emit({"type": "slot", "slot": slot, "call": self.slots[slot]})
        elif action in ("end", "lost", "timeout"):
            self._finish(slot, b)

    def _finish(self, slot: int, b: Dict[str, Any]) -> None:
        call = self.slots.get(slot)
        self.slots[slot] = None
        if not call:
            self.emit({"type": "slot", "slot": slot, "call": None})
            return
        now = time.time()
        dur = b.get("duration")
        duration = float(dur) if isinstance(dur, (int, float)) else max(0.0, now - call["start"])
        rssi = b.get("rssi", {}).get("ave") if isinstance(b.get("rssi"), dict) else call.get("rssi_live")
        ber = b.get("ber", call.get("ber_live"))
        loss = b.get("loss")
        cur = self.db.x(
            "INSERT INTO calls (ts, end_ts, source, slot, src_id, callsign, dst_id, grp, is_data, duration, ber, loss, rssi, result) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (call["start"], now, call["source"], slot, call["src_id"], call["callsign"], call["dst_id"],
             1 if call["group"] else 0, 1 if call["is_data"] else 0, round(duration, 1),
             None if ber is None else round(float(ber), 2), None if loss is None else round(float(loss), 1),
             None if rssi is None else int(rssi), b.get("action", "end")))
        row = self.db.q("SELECT * FROM calls WHERE id = ?", (cur.lastrowid,))[0]
        entry = self._row(row)
        self.last_heard.insert(0, entry)
        del self.last_heard[40:]
        self.emit({"type": "slot", "slot": slot, "call": None})
        self.emit({"type": "heard", "entry": entry})

    def purge(self, keep_days: int) -> int:
        return self.db.x("DELETE FROM calls WHERE ts < ?", (time.time() - keep_days * 86400,)).rowcount or 0
