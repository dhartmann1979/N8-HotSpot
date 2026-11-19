"""
Start:            python -m n8hotspot
New password:     python -m n8hotspot reset-password [username]
Write ini files:  python -m n8hotspot write-config
Current values:   python -m n8hotspot show-settings          (JSON, used by setup.sh)
Apply setup:      python -m n8hotspot apply-setup FILE.json  (JSON from setup.sh / build-image.sh)
DMR ID lookup:    python -m n8hotspot lookup-id 2621234      (JSON: callsign, name, FreeRadioID)
Find the modem:   python -m n8hotspot scan-serial            (JSON: serial ports and MMDVM answers)
"""
import getpass
import json
import logging
import os
import sys


def _ctx():
    from . import app as a
    a.ctx = a.Ctx()
    return a


def apply_setup(path: str) -> int:
    """{"settings": {...}, "admin": {"username", "password"}, "refresh_ids": true}"""
    a = _ctx()
    data = json.loads(open(path, encoding="utf-8").read())
    changes = {k: v for k, v in (data.get("settings") or {}).items() if v is not None}
    changed = a.ctx.settings.update(changes, "setup")
    print(f"✓ Einstellungen gespeichert ({len(changed)} weichen von der Vorgabe ab)")
    adm = data.get("admin") or {}
    if adm.get("username") and adm.get("password"):
        from .auth import DEFAULT_USER
        db = a.ctx.db
        if adm["username"].lower() != DEFAULT_USER:
            a.ctx.auth.reset(adm["username"], adm["password"])               # creates the admin
            db.x("DELETE FROM users WHERE username = ? AND default_pw = 1", (DEFAULT_USER,))
        else:
            a.ctx.auth.reset(DEFAULT_USER, adm["password"])
        print(f"✓ Admin {adm['username']} angelegt" + (", Werks-Login entfernt" if adm["username"].lower() != DEFAULT_USER else ""))
    a.write_config()
    print("✓ MMDVM-Host.ini und DMRGateway.ini geschrieben")
    if data.get("refresh_ids"):
        try:
            r = a.ctx.refresh_ids()
            de = lambda n: f"{n:,}".replace(",", ".")
            print(f"✓ DMR-ID-Liste: {de(r.get('ids', 0))} IDs" +
                  (f" · FreeRadioID.net: {de(r['frid'])} registrierte IDs" if r.get("frid") else ""))
        except Exception as e:
            print(f"! DMR-ID-Liste konnte nicht geladen werden ({e}); der Dienst versucht es beim Start erneut")
    return 0


def lookup_id(rid: int) -> int:
    """Callsign/name and FreeRadioID registration for setup.sh (live API, no database needed)."""
    from .freeradioid import FreeRadioID, PROFILE_URL, http_get
    out = {"id": rid, "found": False}
    try:
        raw = json.loads(http_get(PROFILE_URL.format(id=rid), 65536, 8).decode("utf-8", "replace"))
        res = raw.get("results") or []
        if res:
            r = res[0]
            out.update(found=True, registered=bool(raw.get("reg")), callsign=r.get("callsign") or "",
                       name=" ".join(x for x in (r.get("fname"), r.get("surname")) if x),
                       city=r.get("city") or "", country=r.get("country") or "")
    except Exception as e:
        out["error"] = str(e)
    print(json.dumps(out, ensure_ascii=False))
    return 0


def main(argv):
    logging.basicConfig(level=logging.WARNING if len(argv) > 1 else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "reset-password":
        user = argv[2] if len(argv) > 2 else "n8schicht"
        pw = os.environ.get("N8HS_PASSWORD") or getpass.getpass(f"New password for {user}: ")
        _ctx().ctx.auth.reset(user, pw)
        print(f"Password for {user} set. All of {user}'s sessions were ended.")
        return 0
    if cmd == "write-config":
        print(_ctx().write_config())
        return 0
    if cmd == "show-settings":
        a = _ctx()
        s = a.ctx.settings.all()
        s["network.password"] = "set" if s.get("network.password") else ""
        s["_factory_login"] = bool(a.ctx.db.q("SELECT 1 FROM users WHERE default_pw = 1"))
        print(json.dumps(s, ensure_ascii=False))
        return 0
    if cmd == "apply-setup":
        return apply_setup(argv[2])
    if cmd == "scan-serial":
        from .serialscan import scan
        print(json.dumps(scan(), ensure_ascii=False))
        return 0
    if cmd == "lookup-id":
        return lookup_id(int(argv[2]))
    import uvicorn
    uvicorn.run("n8hotspot.app:app", host=os.environ.get("N8HS_BIND", "0.0.0.0"),
                port=int(os.environ.get("N8HS_PORT", "80")), log_level="warning", proxy_headers=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
