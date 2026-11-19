"""
FreeRadioID.net: registered IDs, avatars and profiles (https://freeradioid.net/api-index.html).

* Registered IDs: ``api/local_subscriber_ids.json``, loaded together with the
  DMR ID list. They get the FRID badge, and their names fill gaps in the list.
* Avatars: ``api/idimg-<id>.png`` (500 px PNG, ~750 KB). A hotspot only needs
  the avatars of the stations it actually hears, so they are fetched on
  demand, scaled to 192 px WebP (Pillow) and kept in SQLite. Real avatars are
  re-checked weekly, IDs without one daily. Unregistered IDs are never asked.
* Profiles: ``api/dmr/user/?id=<id>`` for the station detail view, cached for
  an hour in memory.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import sqlite3
import threading
import time
import urllib.request
from typing import Dict, Optional, Tuple

from .db import DB

log = logging.getLogger("n8hotspot.freeradioid")

IDS_URL = "https://freeradioid.net/api/local_subscriber_ids.json"
AVATAR_URL = "https://freeradioid.net/api/idimg-{id}.png"
PROFILE_URL = "https://freeradioid.net/api/dmr/user/?id={id}"
UA = "N8-Hotspot (DMR Die N8schicht; https://github.com/dhartmann1979/N8-HotSpot)"
SIZE = 192
RECHECK_IMAGE = 7 * 86400
RECHECK_NONE = 86400
PROFILE_TTL = 3600

SCHEMA = """
CREATE TABLE IF NOT EXISTS frid_ids (
    id       INTEGER PRIMARY KEY,
    callsign TEXT NOT NULL,
    name     TEXT NOT NULL DEFAULT '',
    city     TEXT NOT NULL DEFAULT '',
    state    TEXT NOT NULL DEFAULT '',
    country  TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS frid_avatars (
    dmr_id     INTEGER PRIMARY KEY,
    has_avatar INTEGER NOT NULL,
    mime       TEXT,
    data       BLOB,
    fetched_at REAL NOT NULL
);
"""


def http_get(url: str, limit: int = 8 * 1024 * 1024, timeout: float = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit + 1)[:limit]


def sniff(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def shrink(data: bytes) -> Tuple[Optional[str], bytes]:
    """192 px WebP; the original if Pillow is missing or the image is unreadable."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
        im.thumbnail((SIZE, SIZE), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "WEBP", quality=82, method=4)
        return "image/webp", out.getvalue()
    except Exception:
        return sniff(data), data


def parse_registered(body: bytes) -> Dict[int, Dict[str, str]]:
    """{"count": N, "results": [{"id", "callsign", "fname", "city", "state", "country"}]}"""
    raw = json.loads(body.decode("utf-8", "replace"))
    rows = raw.get("results", []) if isinstance(raw, dict) else raw
    out: Dict[int, Dict[str, str]] = {}
    for r in rows or []:
        try:
            rid = int(r["id"])
        except (KeyError, TypeError, ValueError):
            continue
        call = str(r.get("callsign") or "").strip().upper()
        if not call:
            continue
        st = r.get("state")
        out[rid] = {"callsign": call, "name": str(r.get("fname") or r.get("name") or "").strip(),
                    "city": str(r.get("city") or "").strip(), "state": st.strip() if isinstance(st, str) else "",
                    "country": str(r.get("country") or "").strip()}
    return out


class FreeRadioID:
    def __init__(self, db: DB, fetch=http_get):
        self.db = db
        self.fetch = fetch
        self.db.conn.executescript(SCHEMA)
        self._registered = {r["id"] for r in self.db.q("SELECT id FROM frid_ids")}
        self._placeholder: Optional[str] = None
        self._profiles: Dict[int, Tuple[float, Optional[dict]]] = {}
        self._busy: Dict[int, threading.Event] = {}
        self._lock = threading.Lock()
        self.error = ""
        self.updated = 0.0

    # ------------------------------------------------------------ registered IDs
    def is_registered(self, rid: int) -> bool:
        return int(rid or 0) in self._registered or (int(rid or 0) > 9_999_999 and int(rid) // 100 in self._registered)

    def count(self) -> int:
        return len(self._registered)

    def info(self, rid: int) -> Optional[Dict[str, str]]:
        rows = self.db.q("SELECT * FROM frid_ids WHERE id = ?", (int(rid),))
        return dict(rows[0]) if rows else None

    def load_registered(self, body: bytes) -> int:
        regs = parse_registered(body)
        if not regs:
            raise ValueError("the FreeRadioID list is empty")
        self.db.x("DELETE FROM frid_ids")
        self.db.many("INSERT OR REPLACE INTO frid_ids (id, callsign, name, city, state, country) VALUES (?,?,?,?,?,?)",
                     [(i, r["callsign"], r["name"], r["city"], r["state"], r["country"]) for i, r in regs.items()])
        self._registered = set(regs)
        # forget avatars of IDs that are no longer registered
        self.db.x("DELETE FROM frid_avatars WHERE dmr_id NOT IN (SELECT id FROM frid_ids)")
        self.updated, self.error = time.time(), ""
        return len(regs)

    def refresh_registered(self, url: str = IDS_URL) -> int:
        try:
            n = self.load_registered(self.fetch(url, 32 * 1024 * 1024, 60))
            log.info(f"🛡️ FreeRadioID: {n} registered IDs")
            return n
        except Exception as e:
            self.error = str(e)
            log.warning(f"🛡️ FreeRadioID list failed: {e}")
            raise

    # ------------------------------------------------------------ avatars
    def avatar_stats(self) -> Dict[str, int]:
        d = {bool(r["has_avatar"]): r["n"] for r in
             self.db.q("SELECT has_avatar, COUNT(*) AS n FROM frid_avatars GROUP BY has_avatar")}
        return {"with_avatar": d.get(True, 0), "without": d.get(False, 0)}

    def avatar(self, rid: int) -> Optional[Tuple[bool, Optional[str], Optional[bytes], float]]:
        rows = self.db.q("SELECT has_avatar, mime, data, fetched_at FROM frid_avatars WHERE dmr_id = ?", (int(rid),))
        if not rows:
            return None
        r = rows[0]
        return bool(r["has_avatar"]), r["mime"], (bytes(r["data"]) if r["data"] is not None else None), r["fetched_at"]

    def avatar_due(self, rid: int) -> bool:
        a = self.avatar(rid)
        return a is None or time.time() - a[3] > (RECHECK_IMAGE if a[0] else RECHECK_NONE)

    def fetch_avatar(self, rid: int) -> bool:
        """Download, shrink and store one avatar (blocking). True if the ID has an own image."""
        rid = int(rid)
        with self._lock:
            ev = self._busy.get(rid)
            mine = ev is None
            if mine:
                ev = self._busy[rid] = threading.Event()
        if not mine:
            ev.wait(20)
            a = self.avatar(rid)
            return bool(a and a[0])
        try:
            if self._placeholder is None:
                try:
                    self._placeholder = hashlib.md5(self.fetch(AVATAR_URL.format(id=0))).hexdigest()
                except Exception:
                    self._placeholder = ""
            try:
                data = self.fetch(AVATAR_URL.format(id=rid))
            except Exception as e:
                log.debug(f"avatar {rid}: {e}")
                data = b""
            now = time.time()
            if not data or not sniff(data) or hashlib.md5(data).hexdigest() == self._placeholder:
                self.db.x("INSERT OR REPLACE INTO frid_avatars (dmr_id, has_avatar, mime, data, fetched_at) VALUES (?,0,NULL,NULL,?)",
                          (rid, now))
                return False
            mime, small = shrink(data)
            self.db.x("INSERT OR REPLACE INTO frid_avatars (dmr_id, has_avatar, mime, data, fetched_at) VALUES (?,1,?,?,?)",
                      (rid, mime, sqlite3.Binary(small), now))
            return True
        finally:
            with self._lock:
                self._busy.pop(rid, None)
            ev.set()

    def avatar_id(self, rid: int) -> int:
        """Avatars belong to the 7-digit DMR ID; hotspot IDs (262123401) use the base ID."""
        rid = int(rid or 0)
        return rid // 100 if rid > 9_999_999 and rid not in self._registered else rid

    # ------------------------------------------------------------ profiles
    def profile(self, rid: int, live: bool = True) -> Optional[dict]:
        rid = self.avatar_id(rid)
        hit = self._profiles.get(rid)
        if hit and time.time() - hit[0] < PROFILE_TTL:
            return hit[1]
        prof = None
        if live:
            try:
                raw = json.loads(self.fetch(PROFILE_URL.format(id=rid), 65536, 5).decode("utf-8", "replace"))
                res = raw.get("results") or []
                if res:
                    r = res[0]
                    prof = {"registered": bool(raw.get("reg")), "callsign": r.get("callsign") or "",
                            "name": " ".join(x for x in (r.get("fname"), r.get("surname")) if x),
                            "city": r.get("city") or "", "state": r.get("state") if isinstance(r.get("state"), str) else "",
                            "country": r.get("country") or "", "remarks": r.get("remarks") or ""}
            except Exception as e:
                log.debug(f"profile {rid}: {e}")
                if hit:
                    return hit[1]
        if prof is None:
            reg = self.info(rid)
            if reg:
                prof = {**reg, "registered": True, "remarks": ""}
                prof.pop("id", None)
        if prof is not None:
            prof["registered"] = bool(prof.get("registered")) or rid in self._registered
        self._profiles[rid] = (time.time(), prof)
        return prof
