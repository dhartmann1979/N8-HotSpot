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

from . import __version__, configgen, demo, stats
from .auth import Auth, AuthError, DEFAULT_PASSWORD, DEFAULT_USER
from .calib import KEYS, CalSession
from .db import DB
from .idlist import IdList
from .live import Live
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
        self.live = Live(self.db, self.ids.lookup)
        self.system = System(demo=DEMO)
        cal_bin = os.environ.get("N8HS_MMDVMCAL") or (
            f"{sys.executable} {ROOT / 'tools' / 'fake_mmdvmcal.py'}" if DEMO else "/usr/local/bin/MMDVMCal")
        self.cal = CalSession(cal_bin, self.cal_event)
        self.sockets: Dict[WebSocket, Dict[str, Any]] = {}
        self.services: Dict[str, str] = {}
        self.restart_needed = False

    def cal_event(self, ev: Dict[str, Any]) -> None:
        asyncio.ensure_future(broadcast(ev, admin_only=True))


ctx: Optional[Ctx] = None
app = FastAPI(title="N8-Hotspot", docs_url=None, redoc_url=None, openapi_url=None)


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


@app.middleware("http")
async def _mw(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE") \
            and request.headers.get("x-n8") != "1":
        return JSONResponse({"error": "Missing X-N8 header."}, status_code=403)
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
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
        "tg_names": {str(k): v for k, v in tg_names(s["dashboard.tg_names"]).items()},
        "version": __version__, "demo": DEMO,
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
        return {"title": info["title"], "public": False, "user": None, "login_required": True}
    return {**info, "user": u, "default_login": bool(u and u.get("default_pw"))}


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
    names = tg_names(ctx.settings.get("dashboard.tg_names"))
    return await asyncio.to_thread(stats.summary, ctx.db, range, names, ctx.ids.lookup)


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
    r = ctx.auth.login(str(b.get("username", "")), str(b.get("password", "")), ip_of(request),
                       request.headers.get("user-agent", ""), hours)
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


@app.post("/api/admin/apply")
async def apply_config(request: Request):
    u = need_admin(request)
    write_config()
    out = {}
    for svc in ("dmrgateway", "mmdvmhost"):
        out[svc] = (await ctx.system.control(svc, "restart"))["rc"] == 0
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
            "idlist": ctx.ids.status(), "calls": calls["n"], "calls_since": calls["first"],
            "mqtt": ctx.live.mqtt_connected, "app_version": __version__, "demo": DEMO, "data_dir": str(DATA)}


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
            asyncio.get_running_loop().call_later(0.5, lambda: asyncio.ensure_future(ctx.system.control(svc, action)))
            return {"ok": True}
        r = await ctx.system.control(svc, action)
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
        n = await asyncio.to_thread(ctx.ids.refresh, ctx.settings.get("dashboard.idlist_url"))
    except Exception as e:
        raise HTTPError(502, f"Download failed: {e}")
    ctx.auth.audit("idlist_refresh", u["username"], f"{n} IDs", ip_of(request))
    return {"ok": True, "count": n}


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
        await ctx.system.control(svc, "stop")
    await poll_services(force=True)
    try:
        await ctx.cal.start(s["modem.port"], int(s["modem.speed"]), freq)
    except Exception as e:
        for svc in ("dmrgateway", "mmdvmhost"):
            await ctx.system.control(svc, "start")
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
        await ctx.system.control(svc, "start")
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


# ---------------------------------------------------------------- background
async def poll_services(force: bool = False) -> None:
    states = await ctx.system.service_states()
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
    if ctx.ids.count == 0 and not DEMO:
        try:
            await asyncio.to_thread(ctx.ids.refresh, ctx.settings.get("dashboard.idlist_url"))
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
                await asyncio.to_thread(ctx.ids.refresh, ctx.settings.get("dashboard.idlist_url"))
            except Exception:
                pass


@app.on_event("startup")
async def startup():
    global ctx
    if ctx is None:
        ctx = Ctx()
    loop = asyncio.get_running_loop()
    ctx.live.listeners.append(lambda ev: broadcast(ev))
    write_config()
    if DEMO:
        demo.seed_ids(ctx.db)
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
    log.info(f"🌙 N8-Hotspot {__version__} started{' (demo mode)' if DEMO else ''}; data in {DATA}")


@app.on_event("shutdown")
async def shutdown():
    if ctx and ctx.cal.running:
        await ctx.cal.stop()


app.mount("/static", StaticFiles(directory=STATIC), name="static")
