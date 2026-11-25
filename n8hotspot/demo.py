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

STATIONS = [(2621234, "DL1ABC", "Andreas"), (2625001, "DO7DEM", "Andi"), (2627042, "DB9NAC", "Nadine"),
            (2622718, "DK2XYZ", "Klaus"), (2623301, "DG9NAU", "Gerd"), (2624410, "DO1KLM", "Lena"),
            (2629912, "DL7BER", "Bernd"), (2626123, "DM3HH", "Hanna"), (2421180, "PA3XYZ", "Pieter"),
            (2351200, "G4ABC", "John")]
TGS = [(262, 0.30), (265, 0.28), (2624, 0.14), (2623, 0.10), (91, 0.08), (920, 0.05), (263, 0.03), (9, 0.02)]
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
                     (round(random.uniform(0.0, 0.9), 2) if random.random() < 0.8 else round(random.uniform(1.0, 4.5), 2)) if rf
                     else round(random.uniform(0, 0.3), 2),
                     None if rf else round(random.uniform(0, 1.5), 1), random.randint(-78, -55) if rf else None, "end"))
    db.many("INSERT INTO calls (ts, end_ts, source, slot, src_id, callsign, dst_id, grp, is_data, duration, ber, loss, rssi, result) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


FRID_DEMO = {2621234: "Minden", 2625001: "Bielefeld", 2627042: "Hannover", 2622718: "Herford", 2626123: "Hamburg"}
AVATAR_DEMO = (2621234, 2625001, 2627042, 2626123)


def _demo_avatar(seed: int) -> bytes:
    """A made-up landscape picture (demo only; no real person's photo)."""
    import io
    from PIL import Image, ImageDraw
    rnd = random.Random(seed)
    s = 192
    im = Image.new("RGB", (s, s))
    d = ImageDraw.Draw(im)
    top = (rnd.randint(10, 60), rnd.randint(30, 90), rnd.randint(110, 200))
    bot = (rnd.randint(150, 255), rnd.randint(90, 170), rnd.randint(60, 140))
    for y in range(s):
        t = y / s
        d.line([(0, y), (s, y)], fill=tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    d.ellipse([rnd.randint(30, 120), 40, rnd.randint(30, 120) + 42, 82], fill=(255, 226, 140))
    for layer, shade in ((0, 0.55), (1, 0.3)):
        pts = [(0, s)]
        x = 0
        while x <= s:
            pts.append((x, rnd.randint(95, 135) + layer * 25))
            x += rnd.randint(25, 45)
        pts += [(s, s)]
        d.polygon(pts, fill=tuple(int(c * shade) for c in top))
    d.line([(150, 70), (150, 150)], fill=(30, 30, 40), width=4)            # antenna mast
    d.line([(138, 82), (162, 82)], fill=(30, 30, 40), width=3)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=82)
    return out.getvalue()


def seed_ids(db: DB, frid=None) -> None:
    if db.q("SELECT 1 FROM dmrids LIMIT 1"):
        return
    rows = [(i, c, n, FRID_DEMO.get(i, ""), "Germany") for i, c, n in STATIONS]
    db.many("INSERT OR REPLACE INTO dmrids (id, callsign, name, city, country) VALUES (?,?,?,?,?)", rows)
    if frid is not None:
        frows = [(i, c, n, FRID_DEMO[i], "", "Germany") for i, c, n in STATIONS if i in FRID_DEMO]
        db.many("INSERT OR REPLACE INTO frid_ids (id, callsign, name, city, state, country) VALUES (?,?,?,?,?,?)", frows)
        for i in FRID_DEMO:
            img = _demo_avatar(i) if i in AVATAR_DEMO else None
            db.x("INSERT OR REPLACE INTO frid_avatars (dmr_id, has_avatar, mime, data, fetched_at) VALUES (?,?,?,?,?)",
                 (i, 1 if img else 0, "image/webp" if img else None, img, time.time()))
        frid._registered = set(FRID_DEMO)
        frid.updated = time.time() - 3 * 3600


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
    n = 0
    while True:
        await asyncio.sleep(random.uniform(3, 9) if n else 2)
        rf = n == 0 or random.random() < 0.25          # the first call after the start comes over RF (BER, RSSI)
        n += 1
        st = (OWN[0], OWN[1]) if rf else random.choice(STATIONS)[:2]
        tg = _tg()
        src = "rf" if rf else "network"
        pub("mmdvm/json", {"MMDVM": {"mode": "DMR"}})
        pub("mmdvm/json", {"DMR": {"source": src, "action": "start", "slot": 2, "src_id": st[0], "dst_id": tg,
                                    "group": "yes", "src_info": st[1]}})
        pub("mmdvm/log", f"M: {ts()} DMR Slot 2, received {'RF' if rf else 'network'} voice header from {st[1]} to TG {tg}")
        dur = random.uniform(8, 18) if rf else random.uniform(3, 16)
        t0 = time.time()
        weak = n == 1 or random.random() < 0.3                 # now and then a weak signal: higher BER, lower RSSI
        bers = []
        while time.time() - t0 < dur:
            await asyncio.sleep(0.5)
            if rf:
                b = round(max(0.0, random.gauss(2.2 if weak else 0.35, 0.9 if weak else 0.25)), 2)
                bers.append(b)
                pub("mmdvm/json", {"BER": {"mode": "DMR", "slot": 2, "value": b}})
                pub("mmdvm/json", {"RSSI": {"mode": "DMR", "slot": 2, "value": random.randint(-95, -82) if weak else random.randint(-72, -58)}})
        if rf:
            ber = round(sum(bers) / len(bers), 1) if bers else 0.0
            pub("mmdvm/json", {"DMR": {"action": "end", "slot": 2, "duration": round(dur, 1), "ber": ber,
                                        "rssi": {"min": -71, "max": -59, "ave": -64}}})
            pub("mmdvm/log", f"M: {ts()} DMR Slot 2, received RF end of voice transmission from {st[1]} to TG {tg}, {dur:.1f} seconds, BER: {ber}%, RSSI: -71/-59/-64 dBm")
        else:
            loss = round(random.uniform(0, 1), 0)
            pub("mmdvm/json", {"DMR": {"action": "end", "slot": 2, "duration": round(dur, 1), "loss": loss, "ber": 0.0}})
            pub("mmdvm/log", f"M: {ts()} DMR Slot 2, received network end of voice transmission from {st[1]} to TG {tg}, {dur:.1f} seconds, {loss:.0f}% packet loss, BER: 0.0%")
        await asyncio.sleep(1.5)
        pub("mmdvm/json", {"MMDVM": {"mode": "Idle"}})
