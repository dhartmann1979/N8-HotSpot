"""
N8-Hotspot web application (FastAPI).

Environment:
  N8HS_DATA      data directory (database, generated ini files, DMRIds.dat); default <repo>/data
  N8HS_BIND      listen address, default 0.0.0.0
  N8HS_PORT      web port, default 80
  N8HS_DEMO      1 = demo mode (no modem, simulated traffic)
  N8HS_MMDVMCAL  calibration program, default /usr/local/bin/MMDVMCal
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import n8_security as _sec
from . import __version__, configgen, demo, permcheck, siteicons, stats, updater
from .auth import Auth, AuthError, DEFAULT_PASSWORD, DEFAULT_USER
from .calib import KEYS, CalSession
from .db import DB
from .freeradioid import FreeRadioID
from .idlist import IdList
from .talkgroups import Talkgroups
from .uiconfig import UIConfig
from .live import Live
from .n8_admin import N8Admin
from .settings import MASTER_PRESETS, MODEM_PRESETS, Settings, SettingsError, hotspot_id, tg_names
from .system import SERVICES, System

log = logging.getLogger("n8hotspot")
ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DATA = Path(os.environ.get("N8HS_DATA", ROOT / "data"))
DEMO = os.environ.get("N8HS_DEMO", "") not in ("", "0")
COOKIE = "n8hs_session"


class Ctx:
    def __init__(self):
        DATA.mkdir(parents=True, exist_ok=True)
        self.db = DB(DATA / "n8hotspot.db")
        self.auth = Auth(self.db)
        self.settings = Settings(self.db)
        self.ids = IdList(self.db, DATA)
        self.frid = FreeRadioID(self.db)
        self.tgs = Talkgroups(self.db)
        self.live = Live(self.db, self.lookup)
        self.system = System(demo=DEMO)
        cal_bin = os.environ.get("N8HS_MMDVMCAL") or (
            f"{sys.executable} {ROOT / 'tools' / 'fake_mmdvmcal.py'}" if DEMO else "/usr/local/bin/MMDVMCal")
        self.cal = CalSession(cal_bin, self.cal_event)
        self.sockets: Dict[WebSocket, Dict[str, Any]] = {}
        self.services: Dict[str, str] = {}
        self.restart_needed = False
        self.ui = UIConfig(self.db)
        self.icons = siteicons.IconCache(DATA / "n8hotspot.db")
        self.update_lock = asyncio.Lock()
        self.update_last_try = 0.0
        # Dienste, Berechtigungen und „Update jetzt“ – gemeinsames N8 Admin-Kit (scripts/n8-admin.sh, läuft als root per sudo)
        self.n8 = N8Admin(DATA, demo=DEMO)
        if DEMO and not (DATA / "n8-admin.json").exists():      # Demo: was n8-admin.sh sudo-setup schreiben würde
            import json as _json
            units = [("mmdvmhost.service", "MMDVMHost (Modem)", ["start", "stop", "restart", "enable", "disable"]),
                     ("dmrgateway.service", "DMRGateway (DMR-Server)", ["start", "stop", "restart", "enable", "disable"]),
                     ("mosquitto.service", "MQTT (Live-Daten)", ["start", "stop", "restart", "enable", "disable"]),
                     ("n8hotspot.service", "Weboberfläche", ["restart", "enable"]),
                     ("n8hotspot-update.path", "Update-Auslöser („Update jetzt“)", ["start", "stop", "restart", "enable", "disable"])]
            (DATA / "n8-admin.json").write_text(_json.dumps({
                "version": 1, "name": "N8-Hotspot", "id": "n8hotspot", "systemctl": "/usr/bin/systemctl",
                "self": "/opt/n8hotspot/scripts/n8-admin.sh", "update_unit": "n8hotspot-update.service",
                "request": str(DATA / "update.request"), "log": str(DATA / "update.log"), "result": str(DATA / "update.result"),
                "units": [{"unit": u, "label": label, "actions": a} for u, label, a in units]}), "utf-8")

    def lookup(self, rid: int) -> Dict[str, Any]:
        """Callsign/name/place from the ID list, completed by FreeRadioID; 'frid' = registered there."""
        d = dict(self.ids.lookup(rid))
        if rid and self.frid.is_registered(rid):
            info = self.frid.info(self.frid.avatar_id(rid)) or {}
            for k in ("callsign", "name", "city", "country"):
                if not d.get(k) and info.get(k):
                    d[k] = info[k]
            d["frid"] = True
        return d

    def tg_names(self) -> Dict[int, str]:
        """Talkgroup names: the N8schicht list, overridden/completed by the own names."""
        names = dict(self.tgs.names()) if self.settings.get("dashboard.tg_list") else {}
        names.update(tg_names(self.settings.get("dashboard.tg_names")))
        return names

    def refresh_ids(self) -> Dict[str, Any]:
        """ID list (CSV) and the FreeRadioID registered IDs (blocking; runs in a thread)."""
        out: Dict[str, Any] = {}
        if self.settings.get("dashboard.tg_list"):
            try:
                out["talkgroups"] = self.tgs.refresh(self.settings.get("dashboard.tg_url"))
            except Exception as e:
                out["tg_error"] = str(e)
        out["ids"] = self.ids.refresh(self.settings.get("dashboard.idlist_url"))
        if self.settings.get("frid.ids"):
            try:
                out["frid"] = self.frid.refresh_registered()
                rows = [(r["id"], r["callsign"], r["name"], r["city"], r["country"])
                        for r in self.db.q("SELECT * FROM frid_ids")]
                out["frid_added"] = self.ids.merge(rows)
            except Exception as e:
                out["frid_error"] = str(e)
        return out

    def cal_event(self, ev: Dict[str, Any]) -> None:
        asyncio.ensure_future(broadcast(ev, admin_only=True))


ctx: Optional[Ctx] = None
app = FastAPI(title="N8-Hotspot", **{"docs_url": None, "redoc_url": None, "openapi_url": None, **_sec.FASTAPI_KWARGS})


class HTTPError(Exception):
    def __init__(self, status: int, msg: str):
        self.status, self.msg = status, msg


@app.exception_handler(HTTPError)
async def _http_error(request: Request, exc: HTTPError):
    return JSONResponse({"error": exc.msg}, status_code=exc.status)


@app.exception_handler(AuthError)
async def _auth_error(request: Request, exc: AuthError):
    return JSONResponse({"error": str(exc)}, status_code=400)


@app.exception_handler(SettingsError)
async def _settings_error(request: Request, exc: SettingsError):
    return JSONResponse({"error": str(exc)}, status_code=400)


from .n8_guard import Guard, LoginGuard  # noqa: E402
app.add_middleware(Guard, api_per_min=1200, page_per_min=600, auth_per_min=30, max_body=64 * 1024 * 1024)
LOGIN_GUARD = LoginGuard()


@app.middleware("http")
async def _mw(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE") \
            and request.headers.get("x-n8") != "1":
        return JSONResponse({"error": "Missing X-N8 header."}, status_code=403)
    if request.url.path.startswith("/api/admin/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        u = user_of(request)
        if u and u.get("default_pw"):             # factory login: first an own password (👤 → My account)
            return JSONResponse({"error": "Please set your own password first (👤 → My account)."}, status_code=403)
    resp = await call_next(request)
    _sec.headers(resp, https=_sec.is_https(request))
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


# ---------------------------------------------------------------- helpers
def ip_of(conn) -> str:
    return conn.client.host if conn.client else ""


def user_of(conn) -> Optional[Dict[str, Any]]:
    return ctx.auth.session_user(conn.cookies.get(COOKIE))


def public() -> bool:
    return bool(ctx.settings.get("dashboard.public"))


def need_view(request: Request) -> Optional[Dict[str, Any]]:
    u = user_of(request)
    if not u and not public():
        raise HTTPError(401, "Please log in.")
    return u


def need_admin(request: Request) -> Dict[str, Any]:
    u = user_of(request)
    if not u:
        raise HTTPError(401, "Please log in.")
    if u["role"] != "admin":
        raise HTTPError(403, "Admins only.")
    return u


async def body(request: Request) -> Dict[str, Any]:
    try:
        b = await request.json()
    except Exception:
        raise HTTPError(400, "Invalid request.")
    if not isinstance(b, dict):
        raise HTTPError(400, "Invalid request.")
    return b


async def broadcast(ev: Dict[str, Any], admin_only: bool = False) -> None:
    dead = []
    for ws, meta in list(ctx.sockets.items()):
        if admin_only and not meta.get("admin"):
            continue
        if ev.get("type") == "log" and not meta.get("admin"):
            continue
        try:
            await ws.send_json(ev)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ctx.sockets.pop(ws, None)


def write_config() -> Dict[str, bool]:
    return configgen.write_all(ctx.settings.all(), DATA)


def station_info() -> Dict[str, Any]:
    s = ctx.settings.all()
    duplex = bool(s["modem.duplex"])
    return {
        "title": s["dashboard.title"], "callsign": s["station.callsign"], "dmr_id": s["station.dmr_id"],
        "hotspot_id": hotspot_id(s), "location": s["station.location"], "rx_freq": s["modem.rx_freq"],
        "tx_freq": s["modem.tx_freq"] if duplex else s["modem.rx_freq"], "duplex": duplex,
        "color_code": s["dmr.color_code"], "slot1": duplex and s["dmr.slot1"], "slot2": s["dmr.slot2"],
        "network": s["network.name"] if s["network.enabled"] else "", "network_host": s["network.host"],
        "modem": MODEM_PRESETS.get(s["modem.preset"], ("",))[0], "public": s["dashboard.public"],
        "tg_names": {str(k): v for k, v in ctx.tg_names().items()},
        "version": __version__, "demo": DEMO, "avatars": bool(s["frid.avatars"]),
    }


# ---------------------------------------------------------------- pages & public API
@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/info")
async def api_info(request: Request):
    u = user_of(request)
    info = station_info()
    if not u and not info["public"]:
        return {"title": info["title"], "public": False, "user": None, "login_required": True, **ui_public()}
    return {**info, "user": u, "default_login": bool(u and u.get("default_pw")), **ui_public()}


# ---------------------------------------------------------------- appearance, links, updates
def ui_public() -> Dict[str, Any]:
    """Colour scheme, link menu and version: needed before login (the login page uses the theme too)."""
    links = ctx.ui.get("links")
    def key(i):
        k = siteicons.key_for(i["url"]) if i.get("site_icon") else None
        return k if k and (not DEMO or ctx.icons.cached(k)) else None
    items = [{**i, "icon_key": key(i)} for i in links["items"]]
    v = updater.local_version()
    return {"theme": ctx.ui.get("theme"), "links": {**links, "items": items},
            "build": {"version": v["version"] or __version__, "commit": v["short"], "date": v["date"]}}


def link_icon_urls() -> list:
    return [i["url"] for i in ctx.ui.get("links")["items"] if i.get("site_icon")]


async def refresh_link_icons(force: bool = False) -> None:
    if DEMO and not os.environ.get("N8HS_FETCH_ICONS"):
        # demo without internet: the N8schicht logo stands in for the site icon of dmr.die-n8schicht.de
        ctx.icons.store("https://dmr.die-n8schicht.de", (STATIC / "n8schicht-icon-192.png").read_bytes(), "image/png")
        return
    try:
        await asyncio.to_thread(ctx.icons.refresh_many, link_icon_urls(), force)
    except Exception as e:      # never fatal
        log.debug(f"link icons: {e}")


@app.get("/api/link-icon/{key}")
async def link_icon(key: str):
    """Site icon of a configured link (from the SQLite cache; fetched once when missing)."""
    urls = {siteicons.key_for(u): u for u in link_icon_urls()}
    if key not in urls:
        raise HTTPError(404, "unknown link")
    hit = ctx.icons.cached(key)
    if hit is None and not DEMO:
        await asyncio.to_thread(ctx.icons.refresh_one, urls[key])
        hit = ctx.icons.cached(key)
    if not hit:
        raise HTTPError(404, "no icon")
    return Response(hit["data"], media_type=hit["content_type"],
                    headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff",
                             "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})


@app.get("/api/admin/ui")
async def get_ui(request: Request):
    need_admin(request)
    links = ctx.ui.get("links")
    return {"theme": ctx.ui.get("theme"), "links": links, "update": ctx.ui.get("update"),
            "icons": {i["url"]: ctx.icons.status(siteicons.key_for(i["url"]) or "") for i in links["items"]
                      if i.get("site_icon")}}


@app.post("/api/admin/ui/{name}")
async def set_ui(name: str, request: Request):
    u = need_admin(request)
    if name not in ("theme", "links", "update"):
        raise HTTPError(404, "unknown")
    v = ctx.ui.set(name, await body(request), u["username"])
    ctx.auth.audit("ui_changed", u["username"], name, ip_of(request))
    if name == "links":
        asyncio.ensure_future(refresh_link_icons(force=True))
    await broadcast({"type": "ui", **ui_public()})
    return {"ok": True, name: v}


@app.post("/api/admin/site-icons/refresh")
async def admin_refresh_site_icons(request: Request):
    u = need_admin(request)
    await refresh_link_icons(force=True)
    links = ctx.ui.get("links")["items"]
    statuses = [ctx.icons.status(siteicons.key_for(item["url"]) or "") for item in links if item.get("site_icon")]
    cached = sum(bool(status and status["ok"]) for status in statuses)
    unavailable = len(statuses) - cached
    ctx.auth.audit("site_icons_refresh", u["username"], f"{cached} cached, {unavailable} unavailable", ip_of(request))
    return {"ok": True, "total": len(statuses), "cached": cached, "unavailable": unavailable}


def _update_cfg() -> Dict[str, Any]:
    return ctx.ui.get("update")


async def update_check(force: bool = False) -> Dict[str, Any]:
    c = _update_cfg()
    return await asyncio.to_thread(updater.check, c["repo"], c["branch"], c["interval_hours"] * 3600, force)


@app.get("/api/admin/update")
async def admin_update(request: Request, force: bool = False):
    need_admin(request)
    c = _update_cfg()
    if not c["enabled"] and not force:
        return {"enabled": False, "available": False, "local": updater.local_version(), "config": c}
    res = await update_check(force)
    try:
        import pwd
        owner = pwd.getpwuid(updater.REPO_ROOT.stat().st_uid).pw_name
    except Exception:
        owner = ""
    return {"enabled": c["enabled"], **res, "config": c, "can_install": bool(res["local"].get("commit")),
            "result": ctx.n8.update_state().get("result"), "kit": ctx.n8.ready,
            "permissions": await permissions(),
            "systemd": bool(os.environ.get("INVOCATION_ID")), "origin": await asyncio.to_thread(updater.origin_url),
            "path": str(updater.REPO_ROOT), "owner": owner, "demo": DEMO}


async def run_update(expected: str, who: str, ip: str) -> Dict[str, Any]:
    """Shared by "Update now" and auto mode.

    Ab 1.5.0 (N8 Admin-Kit eingerichtet): nur die Anforderung schreiben – n8hotspot-update.path startet als root
    scripts/n8-admin.sh update --auto (vorspulen, Pakete, Dienste, ini-Dateien, Rechte, Neustart, Prüfung, sonst zurück).
    Ohne Kit (Update von 1.4.x, bevor fix-perms lief): der alte Weg als Dienst-Benutzer."""
    async with ctx.update_lock:
        ctx.update_last_try = time.time()
        c = _update_cfg()
        if ctx.n8.ready or DEMO:
            ok, msg = ctx.n8.request_update()
            if not ok:
                raise HTTPError(409, msg)
            ctx.auth.audit("update", who, f"angefordert ({(expected or '')[:7]})", ip)
            log.info(f"⬆️ Update requested by {who} (n8-admin.sh)")
            return {"changed": True, "files": [], "steps": [], "restart": "n8", "message": msg}
        try:
            res = await asyncio.to_thread(updater.install, c["branch"], expected)
        except updater.UpdateError as e:
            ctx.auth.audit("update_failed", who, str(e)[:200], ip)
            raise HTTPError(409, str(e))
        if not res["changed"]:
            return {**res, "steps": [], "restart": "none"}
        steps = []
        if res["requirements_changed"]:
            err = await asyncio.to_thread(updater.pip_install)
            steps.append({"step": "Python packages", "ok": not err, "detail": err})
        if res.get("config_changed") or c["restart_radio"]:
            try:
                write_config()
                steps.append({"step": "ini files written", "ok": True, "detail": ""})
            except Exception as e:
                steps.append({"step": "ini files written", "ok": False, "detail": str(e)[:200]})
            if c["restart_radio"] and not DEMO:
                for svc in ("dmrgateway", "mmdvmhost"):
                    ok = await asyncio.to_thread(updater.systemctl, "restart", svc)
                    steps.append({"step": f"{svc} restarted", "ok": ok, "detail": "" if ok else "sudo rule missing?"})
        perms = await permissions()
        if not perms["ok"]:
            steps.append({"step": "Permissions", "ok": False,
                          "detail": f"{perms['problems']} problem(s) – run once on the console: {perms['fix']}"})
        if any(f.startswith(("systemd/", "scripts/")) for f in res["files"]):
            steps.append({"step": "Service files changed", "ok": False,
                          "detail": f"they need root – run once on the console: {perms['fix']}"})
        ctx.auth.audit("update", who, f"{res['old'][:7]} → {res['new'][:7]}", ip)
        log.info(f"⬆️ Updated by {who}: {res['old'][:7]} → {res['new'][:7]} ({len(res['files'])} files)")
        how = "manual"
        if DEMO:
            how = "none"
        elif os.environ.get("INVOCATION_ID") or os.geteuid() == 0:
            how = "service"
            loop = asyncio.get_running_loop()
            # sudo rule from install.sh allows "systemctl restart n8hotspot.service"; without it systemd
            # (Restart=always) starts the process again after it ended itself.
            def _restart():
                if not updater.systemctl("restart", "n8hotspot"):
                    import signal as _signal
                    from .n8_crash import mark_planned
                    mark_planned(str(DATA), "n8hotspot.service", "Neustart nach dem Update")
                    os.kill(os.getpid(), _signal.SIGTERM)
            loop.call_later(1.5, lambda: loop.run_in_executor(None, _restart))
        return {**res, "steps": steps, "restart": how}


@app.post("/api/admin/update/install")
async def admin_update_install(request: Request):
    u = need_admin(request)
    b = await body(request)
    ip = ip_of(request)
    # no password: an admin session (cookie + CSRF header) is enough – the same in every N8 system
    if ctx.update_lock.locked() or time.time() - ctx.update_last_try < 30:
        raise HTTPError(429, "An update is already running – please wait a moment.")
    res = await run_update(str(b.get("expected") or ""), u["username"], ip)
    return {"ok": True, **res, "version": updater.local_version()}


async def update_task():
    """Check GitHub every interval (default hourly); in auto mode install at the chosen hour when idle."""
    await asyncio.sleep(60)
    while True:
        c = _update_cfg()
        interval_hours = 1 if c["auto"] else c["interval_hours"]
        now = datetime.now()
        next_check = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        while next_check.hour % interval_hours:
            next_check += timedelta(hours=1)
        try:
            if c["enabled"]:
                res = await update_check(force=True)
                if res.get("available"):
                    log.info(f"⬆️ Update available: {res['behind']} new change(s) "
                             f"({res['local'].get('short')} → {(res.get('latest') or {}).get('short')})")
                    await broadcast({"type": "update", "available": True,
                                     "version": res.get("remote_version") or "", "behind": res["behind"]}, admin_only=True)
                    busy = any(ctx.live.slots.values())       # somebody is transmitting right now
                    if c["auto"] and updater.in_window(c["auto_hour"]) and not busy and not ctx.cal.running \
                            and not ctx.update_lock.locked():
                        try:
                            await run_update((res.get("latest") or {}).get("commit", ""), "auto-update", "")
                        except HTTPError as e:
                            log.warning(f"auto update: {e}")
        except Exception as e:
            log.debug(f"update check failed: {e}")
        await asyncio.sleep(max(1, (next_check - datetime.now()).total_seconds()))


async def midnight_site_icon_refresh() -> None:
    """Refresh the configured website icons at local midnight."""
    while True:
        now = time.time()
        tomorrow = datetime.fromtimestamp(now).date() + timedelta(days=1)
        midnight = time.mktime((tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0, -1, -1, -1))
        await asyncio.sleep(max(1, midnight - now))
        try:
            await refresh_link_icons(force=True)
            log.info("Midnight site icon refresh completed (%d links)", len(link_icon_urls()))
        except Exception:
            log.exception("Midnight site icon refresh failed")


@app.get("/api/live")
async def api_live(request: Request):
    need_view(request)
    snap = ctx.live.snapshot()
    snap["services"] = ctx.services
    return snap


@app.get("/api/stats")
async def api_stats(request: Request, range: str = "today"):
    need_view(request)
    if range not in stats.RANGES:
        raise HTTPError(400, "range must be today, 24h, 7d or 30d")
    names = ctx.tg_names()
    return await asyncio.to_thread(stats.summary, ctx.db, range, names, ctx.lookup)


@app.get("/api/signal")
async def api_signal(request: Request):
    """Signal & vocoder: BER/RSSI over RF, packet loss over the network, voice frames – today and the last calls."""
    need_view(request)
    return await asyncio.to_thread(stats.signal, ctx.db)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    u = user_of(ws)
    if not u and not public():
        await ws.close(code=4401)
        return
    await ws.accept()
    ctx.sockets[ws] = {"admin": bool(u and u["role"] == "admin")}
    try:
        snap = ctx.live.snapshot()
        snap["services"] = ctx.services
        await ws.send_json({"type": "hello", "status": snap})
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        ctx.sockets.pop(ws, None)


# ---------------------------------------------------------------- auth
@app.get("/api/auth/me")
async def me(request: Request):
    u = user_of(request)
    return {"user": u, "public": public(), "default_login": bool(u and u.get("default_pw"))}


@app.post("/api/auth/login")
async def login(request: Request):
    b = await body(request)
    hours = 24 * 30 if b.get("remember") else float(ctx.settings.get("dashboard.session_hours"))
    ip, name = ip_of(request), str(b.get("username", ""))[:64]
    if not LOGIN_GUARD.allowed(ip, name):              # 10 failures per IP (any name) in 15 minutes → locked
        return JSONResponse({"error": "Too many failed attempts. Please wait 15 minutes."}, status_code=429)
    try:
        r = ctx.auth.login(name, str(b.get("password", "")), ip, request.headers.get("user-agent", ""), hours)
    except AuthError:
        LOGIN_GUARD.failed(ip, name)
        await asyncio.sleep(0.4)
        raise
    LOGIN_GUARD.ok(ip, name)
    resp = JSONResponse({"user": r["user"], "default_login": r["user"]["default_pw"]})
    resp.set_cookie(COOKIE, r["token"], max_age=r["max_age"] if b.get("remember") else None, httponly=True,
                    samesite="strict", secure=request.url.scheme == "https", path="/")
    return resp


@app.post("/api/auth/logout")
async def logout(request: Request):
    ctx.auth.logout(request.cookies.get(COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


@app.post("/api/auth/password")
async def own_password(request: Request):
    u = user_of(request)
    if not u:
        raise HTTPError(401, "Please log in.")
    b = await body(request)
    out = ctx.auth.change_own(u, str(b.get("old", "")), str(b.get("new", "")), str(b.get("username", "") or ""), ip_of(request))
    return {"user": out}


# ---------------------------------------------------------------- admin: settings
@app.get("/api/admin/settings")
async def get_settings(request: Request):
    need_admin(request)
    return {"sections": ctx.settings.describe(), "restart_needed": ctx.restart_needed,
            "modem_presets": {k: {"label": v[0], "port": v[1], "speed": v[2], "duplex": v[3]} for k, v in MODEM_PRESETS.items()},
            "master_presets": {k: {"label": v[0], "host": v[1], "port": v[2]} for k, v in MASTER_PRESETS.items()}}


@app.post("/api/admin/settings")
async def save_settings(request: Request):
    u = need_admin(request)
    b = await body(request)
    changes = b.get("changes") or {}
    if not isinstance(changes, dict):
        raise HTTPError(400, "Invalid request.")
    changed = ctx.settings.update(changes, u["username"])
    files = write_config()
    if any(f.restart for f in changed) and any(files.values()):
        ctx.restart_needed = True
    if changed:
        ctx.auth.audit("settings_changed", u["username"], ", ".join(f.key for f in changed), ip_of(request))
        await broadcast({"type": "info", "info": station_info()})
    return {"changed": [f.key for f in changed], "restart_needed": ctx.restart_needed}


# ---------------------------------------------------------------- 🌐 Netz, Ports & Domains (N8 Kit 1.4, Vorbild N8 Crosslink)
# Der Hotspot läuft im Heimnetz: kein eigenes HTTPS, daher hier nur 🔌 Ports – alle an einer Stelle.
@app.get("/api/admin/ports")
async def admin_ports(request: Request):
    need_admin(request)
    v = ctx.settings.all()
    return {"intro": "Alle Ports des N8 Hotspot an einer Stelle. Der Hotspot braucht keine Portfreigabe im Router: er verbindet sich nur "
                     "nach draußen (DMR-Server); die Weboberfläche ist für das Heimnetz.",
            "groups": [
                {"title": "🌐 Weboberfläche", "help": "Im Heimnetz unter http://IP:Port.", "rows": [
                    {"key": "web.port", "label": "Web-Port", "dir": "in", "proto": "TCP", "readonly": True,
                     "value": int(os.environ.get("N8HS_PORT", "80") or 80), "help": "steht im systemd-Dienst (N8HS_PORT)"}]},
                {"title": "🛰️ DMR-Netz", "help": "Server und Passwort unter Betrieb → Einstellungen → DMR-Netz.", "rows": [
                    {"key": "network.port", "label": "DMR-Server-Port", "dir": "out", "proto": "UDP", "value": v.get("network.port"),
                     "help": f"zu {v.get('network.host') or '–'} (HomeBrew, Standard 62031)"}]},
                {"title": "📡 Intern (nur dieser Rechner)", "help": "Verbindungen zwischen den Diensten auf dem Hotspot – nichts freigeben.", "rows": [
                    {"key": "mqtt.port", "label": "MQTT (mosquitto)", "dir": "in", "proto": "TCP", "readonly": True, "value": 1883,
                     "help": "Live-Daten von MMDVMHost und DMRGateway an die Weboberfläche (127.0.0.1)"}]},
            ]}


@app.post("/api/admin/ports")
async def admin_ports_save(request: Request):
    u = need_admin(request)
    b = await body(request)
    vals = b.get("values") or {}
    changes = {k: vals[k] for k in ("network.port",) if k in vals and vals[k] != ctx.settings.get(k)}
    try:
        changed = ctx.settings.update(changes, u["username"])
    except Exception as e:  # SettingsError
        raise HTTPError(400, str(e))
    if changed:
        files = write_config()
        if any(f.restart for f in changed) and any(files.values()):
            ctx.restart_needed = True
        ctx.auth.audit("settings_changed", u["username"], ", ".join(f.key for f in changed), ip_of(request))
    return {"ok": True, "changed": [f.key for f in changed],
            "message": ("Gespeichert – DMRGateway neu starten, damit der Port gilt (Admin → System → Dienste)." if changed else "Nichts geändert.")}


@app.post("/api/admin/apply")
async def apply_config(request: Request):
    u = need_admin(request)
    write_config()
    out = {}
    for svc in ("dmrgateway", "mmdvmhost"):
        out[svc] = (await svc_ctl(svc, "restart"))["rc"] == 0
    ctx.restart_needed = False
    ctx.auth.audit("services_restarted", u["username"], "settings applied", ip_of(request))
    await poll_services(force=True)
    return {"ok": all(out.values()), "services": out}


@app.get("/api/admin/config-files")
async def config_files(request: Request):
    need_admin(request)
    write_config()
    out = {}
    for name in ("MMDVM-Host.ini", "DMRGateway.ini"):
        text = (DATA / name).read_text(encoding="utf-8")
        out[name] = "\n".join(("Password=••••••••" if l.startswith("Password=") and "mmdvm" not in l else l)
                              for l in text.splitlines())
    return out


# ---------------------------------------------------------------- admin: users
@app.get("/api/admin/users")
async def users(request: Request):
    need_admin(request)
    return {"users": ctx.auth.users()}


@app.post("/api/admin/users")
async def create_user(request: Request):
    u = need_admin(request)
    b = await body(request)
    return {"user": ctx.auth.create(u, str(b.get("username", "")), str(b.get("password", "")),
                                    str(b.get("role", "viewer")), str(b.get("display_name", "")), ip_of(request))}


@app.patch("/api/admin/users/{uid}")
async def update_user(uid: int, request: Request):
    u = need_admin(request)
    b = await body(request)
    allowed = {k: b[k] for k in ("username", "display_name", "role", "disabled", "password") if k in b}
    return {"user": ctx.auth.update(u, uid, allowed, ip_of(request))}


@app.delete("/api/admin/users/{uid}")
async def delete_user(uid: int, request: Request):
    u = need_admin(request)
    ctx.auth.delete(u, uid, ip_of(request))
    return {"ok": True}


@app.get("/api/admin/sessions")
async def sessions(request: Request):
    need_admin(request)
    return {"sessions": ctx.auth.sessions()}


@app.delete("/api/admin/sessions/{sid}")
async def revoke(sid: str, request: Request):
    u = need_admin(request)
    ctx.auth.revoke(sid)
    ctx.auth.audit("session_revoked", u["username"], sid, ip_of(request))
    return {"ok": True}


@app.get("/api/admin/audit")
async def audit(request: Request):
    need_admin(request)
    return {"entries": ctx.auth.audit_log()}


# ---------------------------------------------------------------- admin: system
@app.get("/api/admin/system")
async def system_info(request: Request):
    need_admin(request)
    await poll_services()
    calls = ctx.db.q("SELECT COUNT(*) AS n, MIN(ts) AS first FROM calls")[0]
    return {"info": ctx.system.info(), "versions": await ctx.system.versions(), "services": ctx.services,
            "idlist": ctx.ids.status(),
            "talkgroups": {"enabled": ctx.settings.get("dashboard.tg_list"), "count": ctx.tgs.count(),
                           "own": len(tg_names(ctx.settings.get("dashboard.tg_names"))), "updated": ctx.tgs.updated,
                           "error": ctx.tgs.error},
            "frid": {"enabled": ctx.settings.get("frid.ids"), "registered": ctx.frid.count(), "updated": ctx.frid.updated,
                     "error": ctx.frid.error, "avatars": ctx.frid.avatar_stats()},
            "calls": calls["n"], "calls_since": calls["first"],
            "mqtt": ctx.live.mqtt_connected, "app_version": __version__, "demo": DEMO, "data_dir": str(DATA)}


async def svc_ctl(svc: str, action: str) -> Dict[str, Any]:
    """Dienst steuern – ein von Hand (oder für die Kalibrierung) gestoppter Dienst wird vom Keep-Alive nicht wieder gestartet."""
    ctx.n8._hold(f"{svc}.service", action)
    return await ctx.system.control(svc, action)


@app.get("/api/n8/health")
async def n8_health(request: Request):
    """Für den Keep-Alive (scripts/n8-admin.sh): Zustand der Teile – nur direkt von diesem Rechner, nie über einen Proxy."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1") or any(h in request.headers for h in ("x-forwarded-for", "x-real-ip", "forwarded", "via")):
        raise HTTPError(403, "local only")
    L, s = ctx.live, ctx.settings.all()
    cal = ctx.cal.running
    link = L.link.get("state")
    has_net = bool(station_info().get("network"))
    modem_open = L.modem.get("open")
    return {"ok": True, "items": {
        "web": {"ok": True},
        "mqtt": {"ok": L.mqtt_connected, "why": "" if L.mqtt_connected else "keine Live-Daten von MQTT (mosquitto)"},
        "modem": {"ok": cal or modem_open is not False, "why": "MMDVMHost hat das Modem nicht geöffnet"},
        "network": {"ok": cal or not has_net or link == "connected",
                    "why": f"nicht beim DMR-Server angemeldet ({link}{' · ' + L.link.get('reason') if L.link.get('reason') else ''})"},
        "calibration": {"ok": True, "running": cal},
    }, "port": s.get("modem.port")}


@app.post("/api/admin/service")
async def service(request: Request):
    u = need_admin(request)
    b = await body(request)
    svc, action = str(b.get("service", "")), str(b.get("action", ""))
    if svc == "n8hotspot" and action == "stop":
        raise HTTPError(400, "Stopping the web interface would lock you out. Use restart.")
    try:
        if svc == "n8hotspot":
            ctx.auth.audit("service", u["username"], f"{svc} {action}", ip_of(request))
            asyncio.get_running_loop().call_later(0.5, lambda: asyncio.ensure_future(svc_ctl(svc, action)))
            return {"ok": True}
        r = await svc_ctl(svc, action)
    except ValueError as e:
        raise HTTPError(400, str(e))
    ctx.auth.audit("service", u["username"], f"{svc} {action}", ip_of(request))
    await poll_services(force=True)
    if r["rc"] != 0:
        raise HTTPError(500, r["out"].strip()[-300:] or "failed")
    return {"ok": True, "services": ctx.services}


@app.post("/api/admin/power")
async def power(request: Request):
    u = need_admin(request)
    b = await body(request)
    action = str(b.get("action", ""))
    if action not in ("reboot", "poweroff"):
        raise HTTPError(400, "unknown action")
    ctx.auth.audit(action, u["username"], "", ip_of(request))
    asyncio.get_running_loop().call_later(1.0, lambda: asyncio.ensure_future(ctx.system.power(action)))
    return {"ok": True}


# ---------------------------------------------------------------- Dienste, Berechtigungen & sudo, Update-Protokoll (N8 Admin-Kit)
@app.get("/api/admin/services")
async def services_get(request: Request):
    need_admin(request)
    return {"ready": ctx.n8.ready or DEMO, "units": await ctx.n8.units()}


@app.post("/api/admin/services/{unit}/{action}")
async def services_action(unit: str, action: str, request: Request):
    u = need_admin(request)
    if unit == "n8hotspot.service" and action == "restart":
        ok = ctx.n8.allowed(unit, action)
        if not ok:
            raise HTTPError(400, "Aktion nicht freigegeben")
        ctx.auth.audit("service", u["username"], f"{unit} {action}", ip_of(request))
        asyncio.get_running_loop().call_later(0.8, lambda: asyncio.ensure_future(ctx.n8.unit_action(unit, action)))
        return {"ok": True, "message": "Weboberfläche startet neu …", "units": await ctx.n8.units(), "self": True}
    ok, out = await ctx.n8.unit_action(unit, action)
    ctx.auth.audit("service", u["username"], f"{unit} {action}" + ("" if ok else f" – {out[:120]}"), ip_of(request))
    if not ok:
        raise HTTPError(400, out or "fehlgeschlagen")
    await poll_services(force=True)
    return {"ok": True, "message": out, "units": await ctx.n8.units()}


@app.get("/api/admin/perms")
async def perms_get(request: Request):
    need_admin(request)
    return await ctx.n8.check_perms()


@app.post("/api/admin/perms/fix")
async def perms_fix(request: Request):
    u = need_admin(request)
    ok, out = await ctx.n8.fix_perms()
    ctx.auth.audit("perms_fix", u["username"], "ok" if ok else "Fehler bleiben", ip_of(request))
    return {"ok": ok, "message": out, "check": await ctx.n8.check_perms()}


# Abstürze (N8 Kit 1.3): crash-hook von scripts/n8-admin.sh (auch MMDVMHost, DMRGateway, MQTT), Keep-Alive und n8_crash.CrashWatch
# schreiben <Datenordner>/crashes.jsonl – gleiche Adressen in allen N8-Systemen
@app.get("/api/admin/crashes")
async def crashes_get(request: Request):
    need_admin(request)
    return await asyncio.to_thread(ctx.n8.crashes)


@app.get("/api/admin/crashes/{cid}")
async def crash_get(cid: str, request: Request):
    need_admin(request)
    txt = await asyncio.to_thread(ctx.n8.crash_log, cid)
    if txt is None:
        raise HTTPError(404, "Befund nicht gefunden")
    return {"id": cid, "log": txt}


@app.post("/api/admin/crashes/ack")
async def crashes_ack(request: Request):
    need_admin(request)
    b = await body(request)
    b = b if isinstance(b, dict) else {}
    ids = b.get("ids") if isinstance(b.get("ids"), list) else []
    return await asyncio.to_thread(ctx.n8.crash_ack, [str(i) for i in ids][:500], bool(b.get("all")))

@app.post("/api/admin/crashes/delete")
async def crashes_delete(request: Request):
    need_admin(request)
    b = await body(request)
    b = b if isinstance(b, dict) else {}
    ids = b.get("ids") if isinstance(b.get("ids"), list) else []
    return await asyncio.to_thread(ctx.n8.crash_delete, [str(i) for i in ids][:500], bool(b.get("all")))


@app.get("/api/admin/keepalive")
async def keepalive_get(request: Request):
    need_admin(request)
    return ctx.n8.keepalive()


@app.post("/api/admin/keepalive")
async def keepalive_set(request: Request):
    u = need_admin(request)
    b = await body(request)
    try:
        c = ctx.n8.keepalive_set(b)
    except (ValueError, TypeError) as e:
        raise HTTPError(400, str(e))
    ctx.auth.audit("keepalive", u["username"], ", ".join(f"{k}={'…' if 'url' in k and v else v}" for k, v in c.items()), ip_of(request))
    return ctx.n8.keepalive()


@app.get("/api/admin/update-log")
async def update_log_get(request: Request):
    need_admin(request)
    st = ctx.n8.update_state()
    if DEMO and not st.get("log"):
        st["log"] = "=== N8-Hotspot: Update gestartet (Demo) ===\n  › Hole Updates (main) …\n  › Version: 1.4.2 → 1.5.0\n=== fertig ==="
    return st


@app.get("/api/admin/logs")
async def logs(request: Request):
    need_admin(request)
    return {"entries": list(ctx.live.logs)}


@app.get("/api/admin/journal")
async def journal(request: Request, service: str = "mmdvmhost", lines: int = 200):
    need_admin(request)
    if service not in SERVICES:
        raise HTTPError(400, "unknown service")
    return {"text": await ctx.system.journal(service, lines)}


@app.post("/api/admin/idlist/refresh")
async def idlist_refresh(request: Request):
    u = need_admin(request)
    try:
        r = await asyncio.to_thread(ctx.refresh_ids)
    except Exception as e:
        raise HTTPError(502, f"Download failed: {e}")
    ctx.auth.audit("idlist_refresh", u["username"], f"{r['ids']} IDs, {r.get('frid', 0)} FreeRadioID, {r.get('talkgroups', 0)} TGs", ip_of(request))
    await broadcast({"type": "info", "info": station_info()})
    return {"ok": True, "count": r["ids"], "frid": r.get("frid"), "frid_error": r.get("frid_error"),
            "talkgroups": r.get("talkgroups"), "tg_error": r.get("tg_error")}


# ---------------------------------------------------------------- admin: find the modem
DEMO_SCAN = [
    {"port": "/dev/ttyAMA0", "real": "", "kind": "gpio", "usb": {}, "users": [{"pid": 812, "name": "MMDVMHost"}],
     "status": "busy", "modem": None, "speed": None},
    {"port": "/dev/serial0", "real": "/dev/ttyAMA0", "kind": "gpio", "usb": {}, "users": [], "status": "alias",
     "alias_of": "/dev/ttyAMA0", "modem": None, "speed": None},
    {"port": "/dev/ttyS0", "real": "", "kind": "gpio-mini", "usb": {}, "users": [], "status": "silent", "modem": None, "speed": None},
    {"port": "/dev/ttyACM0", "real": "", "kind": "usb", "users": [], "status": "modem", "speed": 115200,
     "usb": {"idVendor": "0483", "idProduct": "5740", "manufacturer": "STMicroelectronics", "product": "ZUMspot", "driver": "cdc_acm"},
     "modem": {"protocol": 1, "description": "ZUMspot-v1.6.1 20230805 14.7456MHz ADF7021 FW by CA6JAU GitID #f3bd9ab"}},
]


DEMO_PERMS = {"ok": True, "problems": 0, "critical": False, "fix": "sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms", "items": [
    {"key": "dialout", "label": "Web interface is in the group dialout (modem scan, calibration)", "ok": True, "detail": "", "level": "ok"},
    {"key": "port:/dev/ttyAMA0", "label": "Serial port /dev/ttyAMA0 can be opened", "ok": True, "detail": "group dialout, mode 660", "level": "ok"},
    {"key": "console", "label": "No Linux console on the modem UART", "ok": True, "detail": "", "level": "ok"}]}


async def permissions() -> Dict[str, Any]:
    if DEMO:
        return DEMO_PERMS
    return await asyncio.to_thread(permcheck.check, ctx.settings.get("modem.port"))


@app.get("/api/admin/permissions")
async def admin_permissions(request: Request):
    """Does the web interface have every permission it needs (serial ports, sudo rule, program folder)?"""
    need_admin(request)
    return await permissions()


@app.post("/api/admin/serial/scan")
async def serial_scan(request: Request):
    """Serial ports with their MMDVM answer. Ports in use (by MMDVMHost) are not touched –
    unless the admin asks to stop MMDVMHost for the scan ({"stop_mmdvmhost": true}); it is started again afterwards."""
    u = need_admin(request)
    b = await body(request)
    stopped = False
    if DEMO:
        await asyncio.sleep(1.5)
        ports = [dict(p) for p in DEMO_SCAN]
        if b.get("stop_mmdvmhost"):
            stopped = True
            for p in ports:
                if p["status"] == "busy":
                    p.update(status="modem", users=[], speed=115200,
                             modem={"protocol": 1, "description": "MMDVM_HS_Hat-v1.6.1 20231115 14.7456MHz ADF7021 FW by CA6JAU"})
    else:
        from . import serialscan
        if b.get("stop_mmdvmhost"):
            if ctx.cal.running:
                raise HTTPError(409, "The calibration is running – stop it first.")
            ctx.n8._hold("mmdvmhost.service", "stop")         # Keep-Alive: nicht dazwischen starten
            stopped = await asyncio.to_thread(updater.systemctl, "stop", "mmdvmhost")
            if not stopped:
                raise HTTPError(500, "MMDVMHost could not be stopped (sudo rule missing?). " + permcheck.fix_command())
            await asyncio.sleep(1.5)
        try:
            ports = await asyncio.to_thread(serialscan.scan)
        finally:
            if stopped:
                await asyncio.to_thread(updater.systemctl, "start", "mmdvmhost")
                ctx.n8._hold("mmdvmhost.service", "start")
        if stopped:
            ctx.auth.audit("service", u["username"], "mmdvmhost stopped for the modem scan", ip_of(request))
    s = ctx.settings.all()
    modem = ctx.live.modem if ctx.live.modem.get("open") else None
    for p in ports:          # the port MMDVMHost has open: what it reported via MQTT
        if p["status"] == "busy" and modem and os.path.realpath(s["modem.port"]) in (p["port"], p.get("real") or p["port"]):
            p["modem"] = {"protocol": modem.get("protocol"), "description": modem.get("description", ""), "via": "MMDVMHost"}
    perms = await permissions()
    return {"ports": ports, "configured": s["modem.port"], "speed": s["modem.speed"], "stopped": stopped,
            "mmdvmhost": ctx.services.get("mmdvmhost", "unknown"),
            "permissions": {"ok": perms["ok"], "fix": perms["fix"],
                            "problems": [i for i in perms["items"] if not i["ok"]]}}


# ---------------------------------------------------------------- talkgroups
@app.get("/api/talkgroups")
async def talkgroups(request: Request):
    """All talkgroup names (list + own) and what this hotspot heard on them in 30 days."""
    need_view(request)
    since = time.time() - 30 * 86400
    rows = ctx.db.q("SELECT dst_id, COUNT(*) AS n, SUM(duration) AS d, MAX(ts) AS last FROM calls "
                    "WHERE grp = 1 AND ts >= ? GROUP BY dst_id", (since,))
    own = tg_names(ctx.settings.get("dashboard.tg_names"))
    return {"names": {str(k): v for k, v in ctx.tg_names().items()}, "own": [str(k) for k in own],
            "activity": {str(r["dst_id"]): {"calls": r["n"], "duration": round(r["d"] or 0, 1), "last": r["last"]} for r in rows},
            "list": {"enabled": ctx.settings.get("dashboard.tg_list"), "count": ctx.tgs.count(), "updated": ctx.tgs.updated}}


# ---------------------------------------------------------------- admin: calibration
@app.get("/api/admin/cal")
async def cal_state(request: Request):
    need_admin(request)
    s = ctx.settings.all()
    return {"cal": ctx.cal.snapshot(), "keys": KEYS, "port": s["modem.port"], "speed": s["modem.speed"],
            "rx_freq": s["modem.rx_freq"], "rx_offset": s["modem.rx_offset"], "tx_offset": s["modem.tx_offset"]}


@app.post("/api/admin/cal/start")
async def cal_start(request: Request):
    u = need_admin(request)
    b = await body(request)
    s = ctx.settings.all()
    freq = int(b.get("freq") or s["modem.rx_freq"])
    for svc in ("mmdvmhost", "dmrgateway"):
        await svc_ctl(svc, "stop")
    await poll_services(force=True)
    try:
        await ctx.cal.start(s["modem.port"], int(s["modem.speed"]), freq)
    except Exception as e:
        for svc in ("dmrgateway", "mmdvmhost"):
            await svc_ctl(svc, "start")
        raise HTTPError(500, str(e))
    ctx.auth.audit("calibration_started", u["username"], f"{freq} Hz", ip_of(request))
    return {"cal": ctx.cal.snapshot()}


@app.post("/api/admin/cal/key")
async def cal_key(request: Request):
    need_admin(request)
    b = await body(request)
    try:
        await ctx.cal.key(str(b.get("key", "")))
    except (ValueError, RuntimeError) as e:
        raise HTTPError(400, str(e))
    return {"ok": True}


@app.post("/api/admin/cal/freq")
async def cal_freq(request: Request):
    need_admin(request)
    b = await body(request)
    try:
        if "step" in b:
            await ctx.cal.set_step(int(b["step"]))
        else:
            await ctx.cal.enter_freq(int(b.get("hz", 0)))
    except (ValueError, RuntimeError) as e:
        raise HTTPError(400, str(e))
    return {"ok": True}


@app.post("/api/admin/cal/stop")
async def cal_stop(request: Request):
    u = need_admin(request)
    await ctx.cal.stop()
    write_config()
    for svc in ("dmrgateway", "mmdvmhost"):
        await svc_ctl(svc, "start")
    await poll_services(force=True)
    ctx.auth.audit("calibration_stopped", u["username"], "", ip_of(request))
    return {"cal": ctx.cal.snapshot()}


@app.post("/api/admin/cal/save")
async def cal_save(request: Request):
    u = need_admin(request)
    b = await body(request)
    try:
        off = int(b.get("offset"))
    except (TypeError, ValueError):
        raise HTTPError(400, "No offset.")
    changes = {"modem.rx_offset": off}
    if b.get("tx", True):
        changes["modem.tx_offset"] = off
    ctx.settings.update(changes, u["username"])
    write_config()
    ctx.restart_needed = not ctx.cal.running
    ctx.auth.audit("calibration_saved", u["username"], f"offset {off} Hz", ip_of(request))
    return {"ok": True, "offset": off}


# ---------------------------------------------------------------- FreeRadioID: avatars and station view
def prefetch_avatar(ev: Dict[str, Any]) -> None:
    """When a FreeRadioID member starts talking, fetch the avatar in the background."""
    call = ev.get("call") if ev.get("type") == "slot" else None
    if not call or not call.get("frid") or DEMO or not ctx.settings.get("frid.avatars"):
        return
    aid = ctx.frid.avatar_id(call["src_id"])
    if ctx.frid.avatar_due(aid):
        asyncio.get_running_loop().run_in_executor(None, ctx.frid.fetch_avatar, aid)


@app.get("/api/avatar/{rid}")
async def avatar(rid: int, request: Request):
    need_view(request)
    none = Response(status_code=404, headers={"Cache-Control": "public, max-age=3600"})
    if not ctx.settings.get("frid.avatars") or not ctx.frid.is_registered(rid):
        return none
    aid = ctx.frid.avatar_id(rid)
    if ctx.frid.avatar_due(aid) and not DEMO:
        try:
            await asyncio.wait_for(asyncio.to_thread(ctx.frid.fetch_avatar, aid), 12)
        except asyncio.TimeoutError:
            pass
    a = ctx.frid.avatar(aid)
    if not a or not a[0]:
        return none
    return Response(a[2], media_type=a[1] or "image/webp", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/station/{rid}")
async def station(rid: int, request: Request):
    """Station view: FreeRadioID profile plus what this hotspot heard from the station."""
    need_view(request)
    info = ctx.lookup(rid)
    prof = None
    if ctx.settings.get("frid.profiles") and not DEMO:
        prof = await asyncio.to_thread(ctx.frid.profile, rid)
    if prof is None and info:
        prof = {"callsign": info.get("callsign", ""), "name": info.get("name", ""), "city": info.get("city", ""),
                "country": info.get("country", ""), "registered": bool(info.get("frid")), "remarks": ""}
    since = time.time() - 30 * 86400
    agg = ctx.db.q("SELECT COUNT(*) AS n, COALESCE(SUM(duration),0) AS d, MIN(ts) AS first, MAX(ts) AS last, "
                   "SUM(source='rf') AS rf, AVG(CASE WHEN source='rf' THEN ber END) AS ber "
                   "FROM calls WHERE src_id = ? AND ts >= ?", (rid, since))[0]
    tgs = ctx.db.q("SELECT dst_id, COUNT(*) AS n, SUM(duration) AS d FROM calls WHERE src_id = ? AND ts >= ? AND grp = 1 "
                   "GROUP BY dst_id ORDER BY d DESC LIMIT 5", (rid, since))
    recent = ctx.db.q("SELECT ts, source, slot, dst_id, grp, duration, ber, loss, rssi FROM calls WHERE src_id = ? "
                      "ORDER BY ts DESC LIMIT 8", (rid,))
    names = ctx.tg_names()
    return {
        "id": rid, "callsign": (prof or {}).get("callsign") or info.get("callsign", ""),
        "frid": bool(info.get("frid")) or bool(prof and prof.get("registered")),
        "avatar": f"/api/avatar/{rid}" if ctx.settings.get("frid.avatars") and info.get("frid") else None,
        "profile": prof,
        "heard": {"calls": agg["n"], "duration": round(agg["d"], 1), "first": agg["first"], "last": agg["last"],
                  "rf_calls": agg["rf"] or 0, "rf_ber": None if agg["ber"] is None else round(agg["ber"], 2)},
        "talkgroups": [{"tg": r["dst_id"], "name": names.get(r["dst_id"], ""), "calls": r["n"], "duration": round(r["d"], 1)} for r in tgs],
        "recent": [{**dict(r), "group": bool(r["grp"])} for r in recent],
    }


# ---------------------------------------------------------------- background
_modem_probe = {"pid": "", "at": 0.0}


async def probe_modem(states: Dict[str, str]) -> None:
    """MMDVMHost meldet „Modem geöffnet“ nur einmal beim Start. Lief er schon, als die Weboberfläche neu startete
    (z. B. nach einem Update), fehlt die Meldung – dann aus dem Journal des laufenden MMDVMHost-Prozesses nachholen."""
    if DEMO or ctx.live.modem.get("open") is not None or states.get("mmdvmhost") != "active":
        return
    now = time.time()
    if now - _modem_probe["at"] < 15:
        return
    _modem_probe["at"] = now
    from .system import run
    r = await run(["systemctl", "show", "-p", "MainPID", "--value", "mmdvmhost.service"], 5)
    pid = r["out"].strip()
    if r["rc"] != 0 or not pid.isdigit() or pid == "0":
        return
    r = await run(["journalctl", "_SYSTEMD_UNIT=mmdvmhost.service", f"_PID={pid}", "-o", "cat", "--no-pager", "-n", "400"], 10)
    if r["rc"] == 0 and ctx.live.modem_from_journal(r["out"].splitlines()):
        log.info(f"Modem-Zustand aus dem Journal von MMDVMHost (PID {pid}): {ctx.live.modem}")


async def poll_services(force: bool = False) -> None:
    states = await ctx.system.service_states()
    try:
        await probe_modem(states)
    except Exception:
        log.exception("modem probe")
    if force or states != ctx.services:
        ctx.services = states
        snap = ctx.live.snapshot()
        snap["services"] = states
        await broadcast({"type": "status", "status": snap})


async def services_task():
    while True:
        try:
            await poll_services()
        except Exception:
            log.exception("service poll")
        await asyncio.sleep(5)


def _next(hhmm: str) -> float:
    h, m = (int(x) for x in hhmm.split(":"))
    now = datetime.now()
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if t <= now:
        t += timedelta(days=1)
    return (t - now).total_seconds()


async def daily_task():
    if (ctx.ids.count == 0 or (ctx.settings.get("frid.ids") and ctx.frid.count() == 0)) and not DEMO:
        try:
            await asyncio.to_thread(ctx.refresh_ids)
        except Exception:
            pass
    while True:
        try:
            ctx.live.purge(int(ctx.settings.get("dashboard.keep_days")))
        except Exception:
            log.exception("purge")
        await asyncio.sleep(_next(ctx.settings.get("dashboard.idlist_time")))
        if not DEMO:
            try:
                await asyncio.to_thread(ctx.refresh_ids)
            except Exception:
                pass


CRASH_SERVICES = [   # welcher Teil der Weboberfläche steckt in einem Stack (Absturz-Befunde, auch für den crash-hook)
    (r"/n8hotspot/live\.py$", "Live-Daten (MQTT)"), (r"/n8hotspot/calib\.py$", "Kalibrierung"), (r"/n8hotspot/configgen\.py$", "Konfiguration (ini)"),
    (r"/n8hotspot/(freeradioid|idlist|talkgroups)\.py$", "ID-Listen"), (r"/n8hotspot/stats\.py$", "Statistik"), (r"/n8hotspot/db\.py$", "Datenbank"),
    (r"/n8hotspot/updater\.py$", "Update"), (r"/n8hotspot/serialscan\.py$", "Modem-Suche"), (r"/n8hotspot/(system|permcheck)\.py$", "System"),
    (r"/n8hotspot/auth\.py$", "Anmeldung"), (r"/n8hotspot/(settings|uiconfig)\.py$", "Einstellungen"), (r"/n8hotspot/siteicons\.py$", "Site-Icons"),
    (r"/n8hotspot/app\.py$", "Weboberfläche"), (r"/(uvicorn|starlette|fastapi|websockets|paho)/", "Webinterface"),
]


@app.on_event("startup")
async def startup_crashwatch():
    """Absturz-Melder (N8 Kit): Hänger der Event-Loop, abgestürzte Tasks, harter Absturz → Admin → System → 💥 Abstürze."""
    if DEMO:
        return
    try:
        from .n8_crash import CrashWatch
        CrashWatch(str(DATA), app="N8-Hotspot", unit="n8hotspot.service", services=CRASH_SERVICES).install()
    except Exception as e:  # noqa: BLE001
        log.warning("Absturz-Melder nicht aktiv: %s", e)


@app.on_event("startup")
async def startup():
    global ctx
    if ctx is None:
        ctx = Ctx()
    loop = asyncio.get_running_loop()
    ctx.live.listeners.append(lambda ev: broadcast(ev))
    ctx.live.listeners.append(prefetch_avatar)
    write_config()
    if DEMO:
        demo.seed_ids(ctx.db, ctx.frid)
        ctx.ids.count = int(ctx.db.q("SELECT COUNT(*) AS n FROM dmrids")[0]["n"])
        ctx.ids.updated = time.time() - 3 * 3600
        demo.seed_history(ctx.db)
        ctx.live._load_last_heard()
        ctx.live.mqtt_connected = True
        ctx.live.loop = loop
        asyncio.ensure_future(demo.run(ctx.live))
    else:
        ctx.live.start_mqtt(loop, os.environ.get("N8HS_MQTT_HOST", "127.0.0.1"), int(os.environ.get("N8HS_MQTT_PORT", "1883")))
    asyncio.ensure_future(services_task())
    asyncio.ensure_future(daily_task())
    asyncio.ensure_future(update_task())
    asyncio.ensure_future(refresh_link_icons())
    asyncio.ensure_future(midnight_site_icon_refresh())
    log.info(f"🌙 N8-Hotspot {__version__} started{' (demo mode)' if DEMO else ''}; data in {DATA}")


@app.on_event("shutdown")
async def shutdown():
    if ctx and ctx.cal.running:
        await ctx.cal.stop()


app.mount("/static", StaticFiles(directory=STATIC), name="static")
