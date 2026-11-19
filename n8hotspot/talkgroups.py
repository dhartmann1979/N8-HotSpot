"""
Talkgroup names from the N8schicht list
(https://github.com/dhartmann1979/n8schicht/blob/main/talkgroup_ids.json).

Format: {"results": [{"TG-id": "262", "callsign": "DEUTSCHLAND NATIONAL", "id": "262"}, ...]}
("callsign" is the talkgroup's name). A copy ships with N8-Hotspot so names
work offline from the first start; the list is updated daily with the ID list.
Own names from the admin area take precedence.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Dict

from .db import DB

log = logging.getLogger("n8hotspot.talkgroups")
URL = "https://raw.githubusercontent.com/dhartmann1979/n8schicht/main/talkgroup_ids.json"
BUNDLED = Path(__file__).with_name("talkgroup_ids.json")
UA = "N8-Hotspot (DMR Die N8schicht)"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tg_list (
    tg   INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
"""


def _fix(s: str) -> str:
    """Repair names that were stored as UTF-8 read as Windows-1252 ('BADEN-WÃœRTTEMBERG')."""
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s


def parse(body: bytes) -> Dict[int, str]:
    raw = json.loads(body.decode("utf-8-sig", "replace"))
    rows = raw.get("results", []) if isinstance(raw, dict) else raw
    out: Dict[int, str] = {}
    for r in rows or []:
        try:
            tg = int(str(r.get("TG-id") or r.get("tg") or r.get("id")).strip())
        except (TypeError, ValueError):
            continue
        name = _fix(str(r.get("callsign") or r.get("name") or "").strip())
        if not name or name.upper() in ("N/A", "NA", "-") or name == str(tg):
            continue                                      # no information
        out[tg] = name
    return out


class Talkgroups:
    def __init__(self, db: DB):
        self.db = db
        self.db.conn.executescript(SCHEMA)
        self.updated = 0.0
        self.error = ""
        self._names: Dict[int, str] = {r["tg"]: r["name"] for r in self.db.q("SELECT tg, name FROM tg_list")}
        if not self._names and BUNDLED.exists():
            try:
                self._store(parse(BUNDLED.read_bytes()))
            except Exception as e:
                log.warning(f"bundled talkgroup list unreadable: {e}")

    def _store(self, names: Dict[int, str]) -> None:
        self.db.x("DELETE FROM tg_list")
        self.db.many("INSERT INTO tg_list (tg, name) VALUES (?, ?)", list(names.items()))
        self._names = dict(names)

    def names(self) -> Dict[int, str]:
        return self._names

    def count(self) -> int:
        return len(self._names)

    def refresh(self, url: str = URL) -> int:
        try:
            req = urllib.request.Request(url or URL, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                names = parse(r.read(8 * 1024 * 1024))
            if len(names) < 10:
                raise ValueError("the talkgroup list is (almost) empty")
            self._store(names)
            self.updated, self.error = time.time(), ""
            log.info(f"🗂️ Talkgroup list: {len(names)} names")
            return len(names)
        except Exception as e:
            self.error = str(e)
            log.warning(f"🗂️ Talkgroup list from {url} failed: {e}")
            raise
