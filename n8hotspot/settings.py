"""
Every setting of the hotspot, stored in SQLite (table ``settings``).

The admin area edits them; ``configgen`` turns them into MMDVM-Host.ini and
DMRGateway.ini. A setting that was never saved has its default.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .db import DB

FREERADIOID_CSV = "https://freeradioid.net/api/subscriber_ids.csv"
RADIOID_CSV = "https://database.radioid.net/static/user.csv"

# Modem presets: (label, port, speed, duplex)
MODEM_PRESETS: Dict[str, Tuple[str, str, int, bool]] = {
    "hs_hat":   ("MMDVM_HS_Hat on the GPIO header (simplex)", "/dev/ttyAMA0", 115200, False),
    "hs_dual":  ("MMDVM_HS_Dual_Hat on the GPIO header (duplex)", "/dev/ttyAMA0", 115200, True),
    "hs_usb":   ("ZUMspot / HS hat via USB (simplex)", "/dev/ttyACM0", 115200, False),
    "rpt_usb":  ("MMDVM repeater board via USB (duplex)", "/dev/ttyACM0", 115200, True),
    "custom":   ("Other / own values", "", 0, False),
}

MASTER_PRESETS: Dict[str, Tuple[str, str, int]] = {
    "n8schicht": ("DMR Die N8schicht", "dmr.die-n8schicht.de", 62031),
    "custom":    ("Other server (HomeBrew)", "", 62031),
}


class SettingsError(Exception):
    """Message is shown to the user."""


@dataclass(frozen=True)
class Field:
    key: str
    section: str
    label: str
    kind: str                 # text | int | float | bool | choice | freq | password | longtext | time | url
    default: Any
    help: str = ""
    restart: bool = True      # needs a restart of MMDVMHost/DMRGateway
    choices: Sequence[Tuple[Any, str]] = ()
    min: Optional[float] = None
    max: Optional[float] = None
    pattern: str = ""


SECTIONS: List[Tuple[str, str, str]] = [
    ("station", "📻 Station", "Callsign, DMR ID and location"),
    ("modem", "📡 Modem", "Board, port, frequencies and levels"),
    ("network", "🛰️ DMR network", "Server, password and options"),
    ("dmr", "🎚️ DMR mode", "Color code, time slots, hang times"),
    ("dashboard", "🌐 Dashboard", "Title, public view, ID list"),
    ("freeradioid", "🛡️ FreeRadioID.net", "Avatars, profiles and registered IDs"),
    ("expert", "🧪 Expert", "Additional lines for the ini files"),
]

FIELDS: List[Field] = [
    # station
    Field("station.callsign", "station", "Callsign", "text", "N0CALL", "Your callsign, e.g. DL1ABC",
          pattern=r"[A-Za-z0-9]{3,8}"),
    Field("station.dmr_id", "station", "DMR ID", "int", 1234567, "7-digit ID from radioid.net / FreeRadioID.net",
          min=1000000, max=9999999),
    Field("station.suffix", "station", "Hotspot suffix", "text", "01",
          "Two digits that make the hotspot ID unique (DMR ID + suffix, e.g. 262123401). Empty = DMR ID only",
          pattern=r"(|[0-9]{2})"),
    Field("station.location", "station", "Location", "text", "", "City or locator, shown to the server", restart=True),
    Field("station.latitude", "station", "Latitude", "float", 0.0, min=-90, max=90),
    Field("station.longitude", "station", "Longitude", "float", 0.0, min=-180, max=180),
    Field("station.height", "station", "Antenna height (m)", "int", 0, min=0, max=9999),
    Field("station.power", "station", "Power (W)", "int", 1, min=0, max=999),
    Field("station.description", "station", "Description", "text", "N8 Hotspot"),
    Field("station.url", "station", "Website", "text", "https://dmr.die-n8schicht.de"),

    # modem
    Field("modem.preset", "modem", "Modem board", "choice", "hs_hat",
          "Fills port, speed and simplex/duplex", choices=[(k, v[0]) for k, v in MODEM_PRESETS.items()]),
    Field("modem.port", "modem", "Serial port", "text", "/dev/ttyAMA0"),
    Field("modem.speed", "modem", "Port speed", "choice", 115200,
          choices=[(115200, "115200"), (230400, "230400"), (460800, "460800")]),
    Field("modem.duplex", "modem", "Duplex (two time slots)", "bool", False,
          "Off for simplex hotspots (TS2 only)"),
    Field("modem.rx_freq", "modem", "RX frequency (MHz)", "freq", 438800000),
    Field("modem.tx_freq", "modem", "TX frequency (MHz)", "freq", 438800000, "Same as RX for simplex"),
    Field("modem.rx_offset", "modem", "RX offset (Hz)", "int", 0, "From the calibration", min=-10000, max=10000),
    Field("modem.tx_offset", "modem", "TX offset (Hz)", "int", 0, "From the calibration", min=-10000, max=10000),
    Field("modem.rx_level", "modem", "RX level (%)", "int", 50, min=0, max=100),
    Field("modem.tx_level", "modem", "TX level (%)", "int", 50, min=0, max=100),
    Field("modem.rf_level", "modem", "RF power (%)", "int", 100, min=0, max=100),
    Field("modem.tx_invert", "modem", "TX invert", "bool", True),
    Field("modem.rx_invert", "modem", "RX invert", "bool", False),
    Field("modem.ptt_invert", "modem", "PTT invert", "bool", False),
    Field("modem.tx_delay", "modem", "TX delay (ms)", "int", 100, min=0, max=1000),
    Field("modem.dmr_delay", "modem", "DMR delay (ms)", "int", 0, min=0, max=1000),

    # network
    Field("network.enabled", "network", "Connect to a DMR server", "bool", True),
    Field("network.preset", "network", "Server", "choice", "n8schicht",
          "Fills name, address and port", choices=[(k, v[0]) for k, v in MASTER_PRESETS.items()]),
    Field("network.name", "network", "Name", "text", "N8schicht", pattern=r"[A-Za-z0-9 ._+-]{1,20}"),
    Field("network.host", "network", "Server address", "text", "dmr.die-n8schicht.de"),
    Field("network.port", "network", "Server port (UDP)", "int", 62031, min=1, max=65535),
    Field("network.password", "network", "Password", "password", "passw0rd",
          "At the N8schicht: your FreeRadioID.net password (full access) or the guest password"),
    Field("network.options", "network", "Options", "text", "", "Optional, e.g. TS1=262;TS2=26500"),
    Field("network.jitter", "network", "Jitter buffer (ms)", "int", 360, min=0, max=2000),

    # dmr
    Field("dmr.color_code", "dmr", "Color code", "int", 1, min=0, max=15),
    Field("dmr.slot1", "dmr", "Time slot 1", "bool", False, "Only used in duplex mode"),
    Field("dmr.slot2", "dmr", "Time slot 2", "bool", True),
    Field("dmr.self_only", "dmr", "Only my own ID may transmit", "bool", False),
    Field("dmr.talker_alias", "dmr", "Send talker alias", "bool", False),
    Field("dmr.call_hang", "dmr", "Call hang (s)", "int", 3, min=0, max=30),
    Field("dmr.tx_hang", "dmr", "TX hang (s)", "int", 4, min=0, max=30),
    Field("dmr.timeout", "dmr", "Timeout (s)", "int", 180, min=0, max=3600),
    Field("dmr.rf_mode_hang", "dmr", "RF mode hang (s)", "int", 10, min=0, max=300),
    Field("dmr.net_mode_hang", "dmr", "Network mode hang (s)", "int", 3, min=0, max=300),
    Field("dmr.cw_id", "dmr", "CW ID", "bool", False, "Morse callsign every 10 minutes"),

    # dashboard
    Field("dashboard.title", "dashboard", "Title", "text", "N8 Hotspot", restart=False),
    Field("dashboard.public", "dashboard", "Public view", "bool", True,
          "Off = only logged-in users see the dashboard", restart=False),
    Field("dashboard.session_hours", "dashboard", "Session length (hours)", "int", 12, min=1, max=720, restart=False),
    Field("dashboard.idlist_url", "dashboard", "DMR ID list", "choice", FREERADIOID_CSV, restart=False,
          choices=[(FREERADIOID_CSV, "FreeRadioID.net (radioid.net + FreeRadioID)"), (RADIOID_CSV, "radioid.net only")]),
    Field("dashboard.idlist_time", "dashboard", "Daily ID list update", "time", "03:27", restart=False),
    Field("dashboard.keep_days", "dashboard", "Keep calls for (days)", "int", 30, min=1, max=365, restart=False),
    Field("dashboard.tg_list", "dashboard", "Talkgroup list of the N8schicht", "bool", True,
          "Names of ~1400 talkgroups (github.com/dhartmann1979/n8schicht), updated daily with the ID list",
          restart=False),
    Field("dashboard.tg_url", "dashboard", "Talkgroup list URL", "text",
          "https://raw.githubusercontent.com/dhartmann1979/n8schicht/main/talkgroup_ids.json",
          "JSON in the format of talkgroup_ids.json", restart=False),
    Field("dashboard.tg_names", "dashboard", "Own talkgroup names", "longtext", "",
          "One per line: 26500 = N8schicht Ortsrunde. Override the list or add missing talkgroups", restart=False),

    # FreeRadioID
    Field("frid.ids", "freeradioid", "Load registered FreeRadioID IDs", "bool", True,
          "Daily with the ID list: FRID badge, names of FreeRadioID-only IDs", restart=False),
    Field("frid.avatars", "freeradioid", "Show avatars", "bool", True,
          "Profile pictures of FreeRadioID members; fetched when a station is heard, cached in the database",
          restart=False),
    Field("frid.profiles", "freeradioid", "Look up profiles", "bool", True,
          "Name, place and remarks in the station view (live from the FreeRadioID API)", restart=False),

    # expert
    Field("expert.mmdvm", "expert", "Extra lines for MMDVM-Host.ini", "longtext", "",
          "[Section] followed by Key=Value lines; they replace or add values", restart=True),
    Field("expert.gateway", "expert", "Extra lines for DMRGateway.ini", "longtext", "", restart=True),
]

BY_KEY: Dict[str, Field] = {f.key: f for f in FIELDS}


def parse_freq(v: Any) -> int:
    """'438.8', '438,8000', '438800000' -> 438800000 Hz."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = float(v)
    else:
        s = str(v).strip().replace(",", ".").lower().replace("mhz", "").strip()
        if not s:
            raise SettingsError("Please enter a frequency.")
        try:
            n = float(s)
        except ValueError:
            raise SettingsError(f"'{v}' is not a frequency.")
    hz = int(round(n * 1_000_000)) if n < 10_000 else int(round(n))
    if not 100_000_000 <= hz <= 1_000_000_000:
        raise SettingsError("Frequency out of range (100–1000 MHz).")
    return hz


def validate(f: Field, raw: Any) -> Any:
    k = f.kind
    if k == "bool":
        if isinstance(raw, str):
            return raw.strip().lower() in ("1", "true", "on", "yes", "ja")
        return bool(raw)
    if k == "int" or (k == "choice" and isinstance(f.default, int)):
        try:
            v = int(str(raw).strip())
        except ValueError:
            raise SettingsError(f"{f.label}: please enter a whole number.")
        if k == "choice" and v not in [c[0] for c in f.choices]:
            raise SettingsError(f"{f.label}: invalid choice.")
        if f.min is not None and v < f.min or f.max is not None and v > f.max:
            raise SettingsError(f"{f.label}: allowed {int(f.min)}–{int(f.max)}.")
        return v
    if k == "float":
        try:
            v = float(str(raw).strip().replace(",", "."))
        except ValueError:
            raise SettingsError(f"{f.label}: please enter a number.")
        if f.min is not None and v < f.min or f.max is not None and v > f.max:
            raise SettingsError(f"{f.label}: allowed {f.min}–{f.max}.")
        return v
    if k == "freq":
        return parse_freq(raw)
    if k == "choice":
        v = str(raw)
        if v not in [str(c[0]) for c in f.choices]:
            raise SettingsError(f"{f.label}: invalid choice.")
        return v
    if k == "time":
        v = str(raw).strip()
        if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", v):
            raise SettingsError(f"{f.label}: format HH:MM.")
        return v
    v = "" if raw is None else str(raw)
    if k != "longtext":
        v = v.strip()
        if "\n" in v or "\r" in v:
            raise SettingsError(f"{f.label}: one line only.")
    if len(v) > 4000:
        raise SettingsError(f"{f.label}: too long.")
    if f.pattern and not re.fullmatch(f.pattern, v):
        raise SettingsError(f"{f.label}: '{v}' is not valid.")
    if f.key == "station.callsign":
        v = v.upper()
    return v


class Settings:
    def __init__(self, db: DB):
        self.db = db

    def all(self) -> Dict[str, Any]:
        stored = {r["key"]: r["value"] for r in self.db.q("SELECT key, value FROM settings")}
        out = {}
        for f in FIELDS:
            out[f.key] = json.loads(stored[f.key]) if f.key in stored else f.default
        return out

    def get(self, key: str) -> Any:
        rows = self.db.q("SELECT value FROM settings WHERE key = ?", (key,))
        return json.loads(rows[0]["value"]) if rows else BY_KEY[key].default

    def meta(self) -> Dict[str, Tuple[float, str]]:
        return {r["key"]: (r["updated_at"], r["updated_by"]) for r in self.db.q("SELECT * FROM settings")}

    def update(self, changes: Dict[str, Any], who: str = "") -> List[Field]:
        """Validate everything first, then store. Returns the fields that changed."""
        current = self.all()
        clean: Dict[str, Any] = {}
        for key, raw in changes.items():
            f = BY_KEY.get(key)
            if not f:
                raise SettingsError(f"Unknown setting: {key}")
            if f.kind == "password" and raw in (None, "", "••••••••"):
                continue          # empty password field = keep the old one
            clean[key] = validate(f, raw)
        merged = {**current, **clean}
        if merged["modem.duplex"] is False and merged["dmr.slot1"] and "dmr.slot1" in clean:
            raise SettingsError("Time slot 1 needs duplex mode.")
        changed = [BY_KEY[k] for k, v in clean.items() if current.get(k) != v]
        now = time.time()
        for f in changed:
            self.db.x("INSERT INTO settings (key, value, updated_at, updated_by) VALUES (?,?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, "
                      "updated_by=excluded.updated_by", (f.key, json.dumps(clean[f.key]), now, who))
        return changed

    def describe(self) -> List[Dict[str, Any]]:
        values, meta = self.all(), self.meta()
        out = []
        for sid, title, sub in SECTIONS:
            fields = []
            for f in FIELDS:
                if f.section != sid:
                    continue
                v = values[f.key]
                if f.kind == "password":
                    v = "••••••••" if v else ""
                ts, by = meta.get(f.key, (None, ""))
                fields.append({"key": f.key, "label": f.label, "kind": f.kind, "value": v, "help": f.help,
                               "restart": f.restart, "choices": [list(c) for c in f.choices],
                               "min": f.min, "max": f.max, "updated_at": ts, "updated_by": by})
            out.append({"id": sid, "title": title, "subtitle": sub, "fields": fields})
        return out


def hotspot_id(values: Dict[str, Any]) -> int:
    base = int(values["station.dmr_id"])
    suf = (values.get("station.suffix") or "").strip()
    return int(f"{base}{suf}") if suf else base


def tg_names(text: str) -> Dict[int, str]:
    names: Dict[int, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s*[=:;\t ]\s*(.+)$", line)
        if m:
            names[int(m.group(1))] = m.group(2).strip()
    return names
