"""Statistics for the charts: per talkgroup, per hour/day, RF vs network, top stations."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from .db import DB

RANGES = ("today", "24h", "7d", "30d")
TOP = 5


def buckets(rng: str, now: Optional[float] = None):
    now_dt = datetime.fromtimestamp(now if now is not None else time.time())
    if rng == "today":
        start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return [start + timedelta(hours=h) for h in range(24)], "hour"
    if rng == "24h":
        last = now_dt.replace(minute=0, second=0, microsecond=0)
        return [last - timedelta(hours=h) for h in range(23, -1, -1)], "hour"
    days = 7 if rng == "7d" else 30
    today = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return [today - timedelta(days=d) for d in range(days - 1, -1, -1)], "day"


def summary(db: DB, rng: str = "today", names: Optional[Dict[int, str]] = None,
            lookup: Callable[[int], Dict[str, str]] = lambda i: {}, now: Optional[float] = None) -> Dict[str, Any]:
    if rng not in RANGES:
        rng = "today"
    names = names or {}
    starts, kind = buckets(rng, now)
    edges = [s.timestamp() for s in starts]
    n = len(edges)
    rows = db.q("SELECT ts, source, src_id, callsign, dst_id, grp, duration, ber FROM calls "
                "WHERE ts >= ? AND is_data = 0 ORDER BY ts", (edges[0],))

    def bucket(ts: float) -> int:
        lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if edges[mid] <= ts:
                lo = mid
            else:
                hi = mid - 1
        return lo

    tgs: Dict[int, Dict[str, Any]] = {}
    per: Dict[int, list] = {}
    stations: Dict[int, Dict[str, Any]] = {}
    rf = {"calls": 0, "duration": 0.0}
    net = {"calls": 0, "duration": 0.0}
    rf_series = [[0, 0.0] for _ in range(n)]
    net_series = [[0, 0.0] for _ in range(n)]
    bers = []
    for r in rows:
        dur, ts, src = float(r["duration"] or 0), float(r["ts"]), r["src_id"]
        b = bucket(ts)
        side = rf if r["source"] == "rf" else net
        side["calls"] += 1
        side["duration"] += dur
        ser = rf_series if r["source"] == "rf" else net_series
        ser[b][0] += 1
        ser[b][1] += dur
        if r["source"] == "rf" and r["ber"] is not None:
            bers.append(float(r["ber"]))
        if src:
            st = stations.setdefault(src, {"id": src, "callsign": r["callsign"] or "", "calls": 0, "duration": 0.0, "last": 0})
            st["calls"] += 1
            st["duration"] += dur
            st["last"] = max(st["last"], ts)
            if r["callsign"]:
                st["callsign"] = r["callsign"]
        if not r["grp"]:
            continue
        tg = int(r["dst_id"] or 0)
        t = tgs.setdefault(tg, {"tg": tg, "calls": 0, "duration": 0.0, "users": set(), "last": 0.0})
        t["calls"] += 1
        t["duration"] += dur
        t["last"] = max(t["last"], ts)
        if src:
            t["users"].add(src)
        pb = per.setdefault(tg, [[0, 0.0] for _ in range(n)])[b]
        pb[0] += 1
        pb[1] += dur

    total = sum(t["duration"] for t in tgs.values()) or 0.0
    ordered = sorted(tgs.values(), key=lambda t: (-t["duration"], -t["calls"], t["tg"]))
    table = [{"tg": t["tg"], "name": names.get(t["tg"], ""), "calls": t["calls"], "duration": round(t["duration"], 1),
              "users": len(t["users"]), "last": t["last"],
              "share": round(t["duration"] / total, 4) if total else 0} for t in ordered[:100]]
    series = [{"tg": t["tg"], "name": names.get(t["tg"], ""),
               "calls": [int(x[0]) for x in per[t["tg"]]], "duration": [round(x[1], 1) for x in per[t["tg"]]]}
              for t in ordered[:TOP]]
    if len(ordered) > TOP:
        oc, od = [0] * n, [0.0] * n
        for t in ordered[TOP:]:
            for i, x in enumerate(per[t["tg"]]):
                oc[i] += int(x[0])
                od[i] += x[1]
        series.append({"tg": None, "name": f"{len(ordered) - TOP} other", "calls": oc, "duration": [round(d, 1) for d in od]})
    top_st = sorted(stations.values(), key=lambda s: -s["duration"])[:10]
    for s in top_st:
        s["duration"] = round(s["duration"], 1)
        info = lookup(s["id"])
        s["callsign"] = s["callsign"] or info.get("callsign", "")
        s["name"] = info.get("name", "")
        s["frid"] = bool(info.get("frid"))
    return {
        "range": rng, "bucket": kind, "buckets": edges,
        "totals": {"calls": rf["calls"] + net["calls"], "duration": round(rf["duration"] + net["duration"], 1),
                   "talkgroups": len(tgs), "stations": len(stations),
                   "rf_calls": rf["calls"], "rf_duration": round(rf["duration"], 1),
                   "net_calls": net["calls"], "net_duration": round(net["duration"], 1),
                   "rf_ber": round(sum(bers) / len(bers), 2) if bers else None},
        "talkgroups": table, "series": series,
        "sources": [{"tg": "rf", "name": "RF (local)", "calls": [x[0] for x in rf_series], "duration": [round(x[1], 1) for x in rf_series]},
                    {"tg": "net", "name": "Network", "calls": [x[0] for x in net_series], "duration": [round(x[1], 1) for x in net_series]}],
        "stations": top_st,
    }
