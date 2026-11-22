"""
Settings of the web interface itself that do not end up in the ini files:
colour scheme (N8 Theme, same engine as HBlink4-FreeRadioID and adn-frn-server),
the link menu in the header and the update check. Stored as JSON in the
``settings`` table under keys starting with ``ui.``.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List

from . import n8theme
from .db import DB
from .settings import SettingsError

LINK_DEFAULT: Dict[str, Any] = {
    "enabled": True, "label": "🔗 Links",
    "items": [
        {"label": "DMR Die N8schicht", "url": "https://dmr.die-n8schicht.de", "icon": "🌙", "new_tab": True, "site_icon": True},
        {"label": "FreeRadioID.net", "url": "https://freeradioid.net", "icon": "🛡️", "new_tab": True, "site_icon": True},
    ],
}
UPDATE_DEFAULT: Dict[str, Any] = {
    "enabled": True, "repo": "dhartmann1979/N8-HotSpot", "branch": "main", "interval_hours": 1,
    "auto": False, "auto_hour": 4, "restart_radio": True,
}
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_RE = re.compile(r"^[A-Za-z0-9_./-]{1,100}$")


def clean_links(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise SettingsError("Links: an object is expected.")
    items = value.get("items") or []
    if not isinstance(items, list):
        raise SettingsError("Links: a list of links is expected.")
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(items[:30], 1):
        if not isinstance(item, dict):
            raise SettingsError(f"Links: entry {i} is not a link.")
        label = str(item.get("label") or "").strip()[:40]
        url = str(item.get("url") or "").strip()[:500]
        if not label and not url:
            continue
        if not label:
            raise SettingsError(f"Links: link {i} needs a name.")
        if not (url.startswith("/") or url.startswith("#") or re.match(r"^(https?://|mailto:)", url, re.I)):
            raise SettingsError(f"Links: „{label}“ must start with https://, mailto:, / or #.")
        if any(c in url for c in "\"'<> "):
            raise SettingsError(f"Links: „{label}“ contains invalid characters.")
        web = bool(re.match(r"^https?://", url, re.I))
        out.append({"label": label, "url": url, "icon": str(item.get("icon") or "").strip()[:8],
                    "new_tab": bool(item.get("new_tab", True)) and (web or url.lower().startswith("mailto:")),
                    "site_icon": web and item.get("site_icon", True) is not False})
    return {"enabled": value.get("enabled", True) is not False,
            "label": (str(value.get("label") or "").strip() or "🔗 Links")[:30], "items": out}


def clean_update(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise SettingsError("Updates: an object is expected.")
    v = {**UPDATE_DEFAULT, **{k: value[k] for k in UPDATE_DEFAULT if k in value}}
    repo, branch = str(v["repo"]).strip(), str(v["branch"]).strip()
    if not _REPO_RE.match(repo):
        raise SettingsError("Updates: repository as owner/name, e.g. dhartmann1979/N8-HotSpot.")
    if not _BRANCH_RE.match(branch) or branch.startswith("-") or ".." in branch:
        raise SettingsError("Updates: invalid branch name.")
    try:
        hours, hour = int(v["interval_hours"]), int(v["auto_hour"])
    except (TypeError, ValueError):
        raise SettingsError("Updates: whole numbers expected.")
    if not 1 <= hours <= 168:
        raise SettingsError("Updates: check every 1–168 hours.")
    if not 0 <= hour <= 23:
        raise SettingsError("Updates: hour 0–23.")
    return {"enabled": bool(v["enabled"]), "repo": repo, "branch": branch, "interval_hours": hours,
            "auto": bool(v["auto"]), "auto_hour": hour, "restart_radio": bool(v["restart_radio"])}


CLEANERS = {
    "theme": (lambda v: n8theme.normalize(v, strict=True), n8theme.DEFAULT),
    "links": (clean_links, LINK_DEFAULT),
    "update": (clean_update, UPDATE_DEFAULT),
}


class UIConfig:
    def __init__(self, db: DB):
        self.db = db

    def get(self, name: str) -> Dict[str, Any]:
        clean, default = CLEANERS[name]
        rows = self.db.q("SELECT value FROM settings WHERE key = ?", ("ui." + name,))
        if not rows:
            return json.loads(json.dumps(default))
        try:
            return clean(json.loads(rows[0]["value"])) if name != "theme" else n8theme.normalize(json.loads(rows[0]["value"]))
        except (ValueError, SettingsError, n8theme.ThemeError):
            return json.loads(json.dumps(default))

    def set(self, name: str, value: Any, who: str = "") -> Dict[str, Any]:
        clean, _ = CLEANERS[name]
        try:
            v = clean(value)
        except n8theme.ThemeError as e:
            raise SettingsError(str(e))
        self.db.x("INSERT INTO settings (key, value, updated_at, updated_by) VALUES (?,?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, "
                  "updated_by=excluded.updated_by", ("ui." + name, json.dumps(v), time.time(), who))
        return v
