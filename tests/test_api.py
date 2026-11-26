import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("N8HS_DATA", str(tmp_path))
    import importlib
    import n8hotspot.app as appmod
    appmod = importlib.reload(appmod)
    monkeypatch.setattr(appmod.Live, "start_mqtt", lambda self, *a, **k: None)
    from fastapi.testclient import TestClient
    with TestClient(appmod.app) as c:
        yield c


H = {"X-N8": "1"}


def test_public_view_and_admin(client):
    assert client.get("/api/info").json()["callsign"] == "N0CALL"
    assert client.get("/api/live").status_code == 200
    assert client.get("/api/admin/settings").status_code == 401
    assert client.post("/api/auth/login", json={"username": "n8schicht", "password": "n8schicht"}).status_code == 403  # no CSRF header
    r = client.post("/api/auth/login", json={"username": "n8schicht", "password": "n8schicht"}, headers=H)
    assert r.status_code == 200 and r.json()["default_login"] is True
    assert client.get("/api/info").json()["default_login"] is True
    # factory login: no admin change before an own password is set
    assert client.post("/api/admin/settings", json={"changes": {"dashboard.public": False}}, headers=H).status_code == 403
    assert client.post("/api/auth/password", json={"old": "n8schicht", "new": "ein-eigenes-pw-1"}, headers=H).status_code == 200
    client.post("/api/auth/login", json={"username": "n8schicht", "password": "ein-eigenes-pw-1"}, headers=H)
    r = client.post("/api/admin/settings", json={"changes": {"dashboard.public": False, "station.callsign": "DL1ABC"}}, headers=H)
    assert r.status_code == 200 and "station.callsign" in r.json()["changed"]
    files = client.get("/api/admin/config-files").json()
    assert "Callsign=DL1ABC" in files["MMDVM-Host.ini"] and "Password=••••••••" in files["DMRGateway.ini"]
    client.post("/api/auth/logout", json={}, headers=H)
    assert client.get("/api/live").status_code == 401                  # private now
    assert client.get("/api/info").json()["login_required"] is True
    assert client.post("/api/admin/settings", json={"changes": {"station.dmr_id": "1"}}, headers=H).status_code == 401


def test_login_lockout_per_ip(client):
    for i in range(10):
        client.post("/api/auth/login", json={"username": f"x{i}", "password": "falsch"}, headers=H)
    r = client.post("/api/auth/login", json={"username": "n8schicht", "password": "n8schicht"}, headers=H)
    assert r.status_code == 429
