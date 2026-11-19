"""
Demo mode (N8HS_DEMO=1): realistic traffic without a modem.

Feeds the same MQTT JSON messages that MMDVMHost and DMRGateway publish into
the live data, and fills the statistics with a few days of calls.
"""
from __future__ import annotations

import asyncio
import json
import random
import time

from .db import DB
from .live import Live

STATIONS = [(2621234, "DL1ABC", "Andreas"), (2625001, "DO5ALF", "Andi"), (2627042, "DB9NAC", "Nadine"),
            (2622718, "DK2XYZ", "Klaus"), (2623301, "DG9NAU", "Gerd"), (2624410, "DO1KLM", "Lena"),
            (2629912, "DL7BER", "Bernd"), (2626123, "DM3HH", "Hanna"), (2421180, "PA3XYZ", "Pieter"),
            (2351200, "G4ABC", "John")]
TGS = [(262, 0.30), (26500, 0.28), (2620, 0.14), (26501, 0.10), (91, 0.08), (9, 0.05), (263, 0.03), (8, 0.02)]
OWN = (2621234, "DL1ABC")


def _tg() -> int:
    r, acc = random.random(), 0.0
    for tg, w in TGS:
        acc += w
        if r <= acc:
            return tg
    return 262


def seed_history(db: DB, days: int = 30) -> None:
    if db.q("SELECT 1 FROM calls LIMIT 1"):
        return
    random.seed(8)
    now = time.time()
    rows = []
    t = now - days * 86400
    while t < now - 60:
        hour = time.localtime(t).tm_hour
        busy = [0.5, 0.3, 0.2, 0.1, 0.1, 0.2, 0.4, 0.7, 0.8, 0.7, 0.6, 0.6, 0.7, 0.6, 0.6, 0.7, 0.8, 1.0, 1.0, 1.0, 0.9, 0.8, 0.7, 0.6][hour]
        t += random.expovariate(busy / 260.0)
        if t >= now - 60:
            break
        st = random.choice(STATIONS)
        rf = random.random() < 0.18
        if rf:
            st = (OWN[0], OWN[1], "Andreas")
        dur = round(random.uniform(2.5, 38.0), 1)
        rows.append((t, t + dur, "rf" if rf else "network", 2, st[0], st[1], _tg(), 1, 0, dur,
                     round(random.uniform(0.0, 0.9), 2) if rf else round(random.uniform(0, 0.3), 2),
                     None if rf else round(random.uniform(0, 1.5), 1), random.randint(-78, -55) if rf else None, "end"))
    db.many("INSERT INTO calls (ts, end_ts, source, slot, src_id, callsign, dst_id, grp, is_data, duration, ber, loss, rssi, result) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


def seed_ids(db: DB) -> None:
    if db.q("SELECT 1 FROM dmrids LIMIT 1"):
        return
    rows = [(i, c, n, "", "Germany") for i, c, n in STATIONS]
    db.many("INSERT OR REPLACE INTO dmrids (id, callsign, name, city, country) VALUES (?,?,?,?,?)", rows)


async def run(live: Live) -> None:
    def pub(topic, obj):
        live.handle(topic, json.dumps(obj) if not isinstance(obj, str) else obj)

    ts = lambda: time.strftime("%Y-%m-%d %H:%M:%S.000", time.gmtime())
    pub("mmdvm/log", f"I: {ts()} MMDVM-Host is starting")
    pub("mmdvm/json", {"Modem": {"open": True, "protocol": 1, "description": "MMDVM_HS_Hat-v1.6.1 20230805 14.7456MHz ADF7021 FW by CA6JAU",
                                 "modes": ["D-Star", "DMR", "YSF", "P25", "NXDN", "POCSAG"], "connection": "uart",
                                 "port": "/dev/ttyAMA0", "speed": 115200}})
    pub("dmr-gateway/json", {"status": {"message": "Opening DMR Network: N8schicht"}})
    await asyncio.sleep(1)
    pub("dmr-gateway/log", f"M: {ts()} N8schicht, Logged into the master successfully")
    pub("dmr-gateway/json", {"status": {"message": "Logged into DMR Network: N8schicht"}})
    pub("mmdvm/json", {"MMDVM": {"mode": "Idle"}})
    random.seed()
    while True:
        await asyncio.sleep(random.uniform(3, 9))
        rf = random.random() < 0.2
        st = (OWN[0], OWN[1]) if rf else random.choice(STATIONS)[:2]
        tg = _tg()
        src = "rf" if rf else "network"
        pub("mmdvm/json", {"MMDVM": {"mode": "DMR"}})
        pub("mmdvm/json", {"DMR": {"source": src, "action": "start", "slot": 2, "src_id": st[0], "dst_id": tg,
                                    "group": "yes", "src_info": st[1]}})
        pub("mmdvm/log", f"M: {ts()} DMR Slot 2, received {'RF' if rf else 'network'} voice header from {st[1]} to TG {tg}")
        dur = random.uniform(3, 16)
        t0 = time.time()
        while time.time() - t0 < dur:
            await asyncio.sleep(1)
            if rf:
                pub("mmdvm/json", {"BER": {"mode": "DMR", "slot": 2, "value": round(random.uniform(0, 0.8), 2)}})
                pub("mmdvm/json", {"RSSI": {"mode": "DMR", "slot": 2, "value": random.randint(-72, -58)}})
        if rf:
            ber = round(random.uniform(0, 0.6), 1)
            pub("mmdvm/json", {"DMR": {"action": "end", "slot": 2, "duration": round(dur, 1), "ber": ber,
                                        "rssi": {"min": -71, "max": -59, "ave": -64}}})
            pub("mmdvm/log", f"M: {ts()} DMR Slot 2, received RF end of voice transmission from {st[1]} to TG {tg}, {dur:.1f} seconds, BER: {ber}%, RSSI: -71/-59/-64 dBm")
        else:
            loss = round(random.uniform(0, 1), 0)
            pub("mmdvm/json", {"DMR": {"action": "end", "slot": 2, "duration": round(dur, 1), "loss": loss, "ber": 0.0}})
            pub("mmdvm/log", f"M: {ts()} DMR Slot 2, received network end of voice transmission from {st[1]} to TG {tg}, {dur:.1f} seconds, {loss:.0f}% packet loss, BER: 0.0%")
        await asyncio.sleep(1.5)
        pub("mmdvm/json", {"MMDVM": {"mode": "Idle"}})
