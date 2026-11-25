"""Appearance (N8 Theme), link menu with site icons and the update check of N8-Hotspot."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot import updater                      # noqa: E402
from n8hotspot.settings import SettingsError        # noqa: E402
from n8hotspot.uiconfig import clean_links, clean_update  # noqa: E402

H = {"X-N8": "1"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("N8HS_DATA", str(tmp_path))
    import importlib
    import n8hotspot.app as appmod
    appmod = importlib.reload(appmod)
    monkeypatch.setattr(appmod.Live, "start_mqtt", lambda self, *a, **k: None)
    monkeypatch.setattr(appmod.siteicons.IconCache, "refresh_many", lambda self, urls, force=False: None)
    from fastapi.testclient import TestClient
    with TestClient(appmod.app) as c:
        c.appmod = appmod
        yield c


def login(c):
    assert c.post("/api/auth/login", json={"username": "n8schicht", "password": "n8schicht"}, headers=H).status_code == 200


def test_links_validation():
    v = clean_links({"items": [{"label": "N8", "url": "https://dmr.die-n8schicht.de"},
                               {"label": "Mail", "url": "mailto:a@b.de", "site_icon": True},
                               {"label": "Local", "url": "/static/x", "new_tab": True},
                               {"label": "", "url": ""}]})
    assert [i["label"] for i in v["items"]] == ["N8", "Mail", "Local"]
    assert v["items"][0]["site_icon"] and not v["items"][1]["site_icon"] and not v["items"][2]["site_icon"]
    assert not v["items"][2]["new_tab"]
    for bad in ("javascript:alert(1)", "https://x.de/\"onload", "ftp://x"):
        with pytest.raises(SettingsError):
            clean_links({"items": [{"label": "x", "url": bad}]})


def test_update_config_validation():
    assert clean_update({})["interval_hours"] == 1
    for bad in ({"repo": "x; rm -rf /"}, {"branch": "--upload-pack=x"}, {"interval_hours": 0}, {"auto_hour": 24}):
        with pytest.raises(SettingsError):
            clean_update(bad)


def test_changelog_notes():
    text = "# Changelog\n\n## [1.2.0] – 2026-12-01\n- new\n\n## [1.1.0] – 2026-11-22\n- updates\n\n## [1.0.0]\n- first\n"
    assert [s["version"] for s in updater.changes_since(text, "1.0.0")] == ["1.2.0", "1.1.0"]
    assert updater.changes_since(text, "1.2.0") == []


def test_theme_links_and_public_info(client):
    info = client.get("/api/info").json()
    assert info["theme"]["preset"] == "n8" and info["links"]["items"] and "build" in info
    assert client.post("/api/admin/ui/theme", json={"preset": "daylight"}, headers=H).status_code == 401
    login(client)
    r = client.post("/api/admin/ui/theme", json={"preset": "ocean", "accent": "#ff8800", "radius": 12}, headers=H)
    assert r.status_code == 200 and r.json()["theme"]["accent"] == "#ff8800"
    assert client.post("/api/admin/ui/theme", json={"preset": "ocean", "accent": "red;}"}, headers=H).status_code == 400
    assert client.get("/api/info").json()["theme"]["preset"] == "ocean"
    r = client.post("/api/admin/ui/links", json={"enabled": True, "label": "Links",
                                                 "items": [{"label": "N8", "url": "https://dmr.die-n8schicht.de/x"}]}, headers=H)
    assert r.status_code == 200
    item = client.get("/api/info").json()["links"]["items"][0]
    assert item["icon_key"]
    # icon served from the SQLite cache, only for configured links
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
    assert client.appmod.ctx.icons.store("https://dmr.die-n8schicht.de", png, "image/png")
    r = client.get(f"/api/link-icon/{item['icon_key']}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content == png
    assert client.get("/api/link-icon/" + "0" * 64).status_code == 404


def test_update_needs_password(client, monkeypatch):
    login(client)
    called = []
    monkeypatch.setattr(updater, "install", lambda branch, expected: called.append(expected) or
                        {"old": "a" * 40, "new": "b" * 40, "files": [], "changed": False, "requirements_changed": False})
    r = client.post("/api/admin/update/install", json={"password": "wrong", "expected": "b" * 40}, headers=H)
    assert r.status_code == 403 and not called
    r = client.post("/api/admin/update/install", json={"password": "n8schicht", "expected": "b" * 40}, headers=H)
    assert r.status_code == 200 and called == ["b" * 40] and r.json()["restart"] == "none"


def test_install_rejects_bad_input():
    for exp in ("", "HEAD", "abc"):
        with pytest.raises(updater.UpdateError):
            updater.install("main", exp)
    with pytest.raises(updater.UpdateError):
        updater.install("-x", "a" * 40)


def test_permission_check_shape(tmp_path):
    from n8hotspot import permcheck
    r = permcheck.check(str(tmp_path / "ttyNOPE"))
    keys = [i["key"] for i in r["items"]]
    assert "dialout" in keys and "port-missing" in keys and "sudo" not in keys      # sudo/program: N8 Admin-Kit
    assert r["fix"].endswith("scripts/n8-admin.sh fix-perms") and r["problems"] == sum(not i["ok"] for i in r["items"])


def test_scan_reports_permissions(client):
    login(client)
    r = client.post("/api/admin/serial/scan", json={}, headers=H)
    assert r.status_code == 200 and "permissions" in r.json() and r.json()["stopped"] is False
    p = client.get("/api/admin/permissions").json()
    assert {"ok", "items", "fix"} <= set(p)


def test_admin_kit_endpoints(client):
    """Dienste, Berechtigungen & sudo, Update-Protokoll (N8 Admin-Kit, Demo)."""
    import json
    n8 = client.appmod.ctx.n8
    n8.demo = True
    acts = ["start", "stop", "restart", "enable", "disable"]
    (n8.state_dir / "n8-admin.json").write_text(json.dumps({"self": "/opt/n8hotspot/scripts/n8-admin.sh", "request": str(n8.state_dir / "update.request"),
        "units": [{"unit": u, "label": u, "actions": acts} for u in ("mmdvmhost.service", "dmrgateway.service", "mosquitto.service")]
        + [{"unit": "n8hotspot.service", "label": "web", "actions": ["restart", "enable"]}]}))
    login(client)
    d = client.get("/api/admin/services").json()
    units = {u["unit"]: u for u in d["units"]}
    assert {"mmdvmhost.service", "dmrgateway.service", "mosquitto.service", "n8hotspot.service"} <= set(units)
    assert "stop" not in units["n8hotspot.service"]["actions"]
    assert client.post("/api/admin/services/n8hotspot.service/stop", json={}, headers=H).status_code == 400
    assert client.post("/api/admin/services/sshd.service/restart", json={}, headers=H).status_code == 400
    r = client.post("/api/admin/services/mmdvmhost.service/disable", json={}, headers=H).json()
    assert {u["unit"]: u for u in r["units"]}["mmdvmhost.service"]["enabled"] == "disabled"
    assert client.get("/api/admin/perms").json()["ok"]
    assert client.post("/api/admin/perms/fix", json={}, headers=H).json()["ok"]
    assert "log" in client.get("/api/admin/update-log").json()


def test_signal_statistics(client):
    login(client)
    d = client.get("/api/signal").json()
    t = d["today"]
    assert {"ber_avg", "ber_good", "ber_mid", "ber_bad", "rssi_avg", "loss_avg", "frames_rf", "frames_net", "frames_lost"} <= set(t)
    assert len(d["hours"]) == 24 and d["frames_per_second"] == 50 and len(d["recent"]) <= 40
    assert t["frames_rf"] >= 0 and t["ber_good"] + t["ber_mid"] + t["ber_bad"] <= t["rf_calls"]


def test_live_view_is_a_radio():
    html = (ROOT / "static" / "index.html").read_text()
    for k in ('id="ledRx"', 'id="ledTx"', 'id="ledMode"', 'class="lcd"', 'id="chBerLive"', 'id="chRecent"', 'id="qBar"'):
        assert k in html, k


def test_keepalive_and_health(client):
    """Keep-Alive: /api/n8/health nur lokal, Einstellungen speichern und prüfen."""
    r = client.get("/api/n8/health")                    # TestClient = "testclient", nicht 127.0.0.1
    assert r.status_code == 403
    login(client)
    d = client.get("/api/admin/keepalive").json()
    assert d["conf"]["enabled"] is True and "checks" in d or "ready" in d
    d = client.post("/api/admin/keepalive", json={"heartbeat_url": "https://hc-ping.com/abc-123", "net_restart": False}, headers=H).json()
    assert d["conf"]["heartbeat_url"] == "https://hc-ping.com/abc-123" and d["conf"]["net_restart"] is False
    assert client.post("/api/admin/keepalive", json={"heartbeat_url": "https://x/$(id)"}, headers=H).status_code == 400
    assert client.post("/api/admin/keepalive", json={"pause_minutes": 60}, headers=H).json()["conf"]["paused_until"] > 0
