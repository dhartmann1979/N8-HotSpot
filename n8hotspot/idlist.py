"""
DMR ID list: callsign, name and city for every DMR ID.

Default source is the combined list of FreeRadioID.net (radioid.net plus the
FreeRadioID IDs). It is stored in SQLite for the dashboard and written as
DMRIds.dat for MMDVMHost (tab separated: id, callsign, name).
"""
from __future__ import annotations

import csv
import gzip
import io
import logging
import os
import time
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterator, Tuple

from .db import DB

log = logging.getLogger("n8hotspot.idlist")
UA = "N8-Hotspot (DMR Die N8schicht; https://github.com/dhartmann1979/N8-Hotspot)"
FRID_FIELDS = ("RADIO_ID", "CALLSIGN", "FIRST_NAME", "CITY", "STATE", "COUNTRY")


def parse_csv(body: bytes) -> Iterator[Tuple[int, str, str, str, str]]:
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    text = body.decode("utf-8", "replace").lstrip("﻿")
    first = text.split("\n", 1)[0]
    if first.split(",", 1)[0].strip().isdigit():
        reader = csv.DictReader(io.StringIO(text, newline=""), fieldnames=list(FRID_FIELDS))
    else:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        reader.fieldnames = [f.strip().upper() for f in (reader.fieldnames or [])]
    for row in reader:
        try:
            rid = int(str(row.get("RADIO_ID", "")).strip())
        except ValueError:
            continue
        call = (row.get("CALLSIGN") or "").strip().upper()
        if not call:
            continue
        yield rid, call, (row.get("FIRST_NAME") or "").strip(), (row.get("CITY") or "").strip(), \
            (row.get("COUNTRY") or "").strip()


class IdList:
    def __init__(self, db: DB, data_dir: Path):
        self.db = db
        self.data_dir = data_dir
        self.updated = 0.0
        self.count = 0
        self.error = ""
        meta = data_dir / "DMRIds.dat"
        if meta.exists():
            self.updated = meta.stat().st_mtime
        self.count = int(self.db.q("SELECT COUNT(*) AS n FROM dmrids")[0]["n"])

    @lru_cache(maxsize=4096)
    def _cached(self, rid: int, gen: int) -> Tuple[str, str, str, str]:
        rows = self.db.q("SELECT callsign, name, city, country FROM dmrids WHERE id = ?", (rid,))
        if not rows and rid > 9999999:          # hotspot IDs with suffix: 262123401 -> 2621234
            rows = self.db.q("SELECT callsign, name, city, country FROM dmrids WHERE id = ?", (rid // 100,))
        return tuple(rows[0]) if rows else ("", "", "", "")

    def lookup(self, rid: int) -> Dict[str, str]:
        if not rid:
            return {}
        c, n, ci, co = self._cached(int(rid), int(self.updated))
        return {"callsign": c, "name": n, "city": ci, "country": co} if c else {}

    def status(self) -> Dict[str, object]:
        return {"count": self.count, "updated": self.updated, "error": self.error}

    def load_bytes(self, body: bytes) -> int:
        rows = list(parse_csv(body))
        if len(rows) < 10:
            raise ValueError("the list is (almost) empty")
        self.db.x("DELETE FROM dmrids")
        self.db.many("INSERT OR REPLACE INTO dmrids (id, callsign, name, city, country) VALUES (?,?,?,?,?)", rows)
        tmp = self.data_dir / "DMRIds.dat.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for rid, call, name, _, _ in rows:
                f.write(f"{rid}\t{call}\t{name}\n")
        os.replace(tmp, self.data_dir / "DMRIds.dat")
        self.count, self.updated, self.error = len(rows), time.time(), ""
        self._cached.cache_clear()
        return len(rows)

    def refresh(self, url: str) -> int:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            n = self.load_bytes(body)
            log.info(f"📘 DMR ID list: {n} IDs from {url}")
            return n
        except Exception as e:
            self.error = str(e)
            log.warning(f"📘 DMR ID list from {url} failed: {e}")
            raise
