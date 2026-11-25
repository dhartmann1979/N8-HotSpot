"""Hardening (N8 security), N8 Admin-Kit and N8 Kit files."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot import n8_security  # noqa: E402


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


def test_api_docs_off(client):
    for p in ("/docs", "/redoc", "/openapi.json"):
        r = client.get(p)
        assert "swagger" not in r.text.lower() and '"paths"' not in r.text, p


def test_security_headers(client):
    h = client.get("/api/info").headers
    csp = h["content-security-policy"]
    for part in ("default-src 'self'", "object-src 'none'", "base-uri 'self'", "frame-ancestors 'self'", "form-action 'self'"):
        assert part in csp
    assert "camera=()" in h["permissions-policy"]
    assert h["x-frame-options"] == "SAMEORIGIN" and h["x-content-type-options"] == "nosniff"
    assert "strict-transport-security" not in h and "server" not in h
    assert "max-age" in client.get("/api/info", headers={"X-Forwarded-Proto": "https"}).headers["strict-transport-security"]


def test_uvicorn_without_server_header():
    assert n8_security.UVICORN_KWARGS == {"server_header": False}
    assert "UVICORN_KWARGS" in (ROOT / "n8hotspot" / "__main__.py").read_text()


def test_update_runs_through_the_admin_kit():
    """Ab 1.5.0: kein update guard mehr in der Unit – „Update jetzt“ läuft über scripts/n8-admin.sh (Path-Unit, root)."""
    unit = (ROOT / "systemd" / "n8hotspot.service").read_text()
    assert "n8-update-guard" not in unit and "NoNewPrivileges=yes" not in unit
    conf = (ROOT / "scripts" / "n8-admin.conf").read_text()
    for k in ("N8_ID=n8hotspot", "mmdvmhost.service", "dmrgateway.service", "n8_check_extra", "n8_fix_extra", "/api/auth/me"):
        assert k in conf, k
    import subprocess as sp
    assert sp.run(["bash", "-n", str(ROOT / "scripts" / "n8-admin.sh")]).returncode == 0
    assert sp.run(["bash", "-n", str(ROOT / "scripts" / "n8-admin.conf")]).returncode == 0


def test_admin_kit_identical_in_other_projects():
    for repo in ("hobbyradioportal", "hblink4-freeradioid", "adn-frn-server"):
        o = ROOT.parent / repo / "scripts" / "n8-admin.sh"
        if o.exists():
            assert o.read_bytes() == (ROOT / "scripts" / "n8-admin.sh").read_bytes(), repo
    o = ROOT.parent / "hobbyradioportal" / "portal" / "n8_admin.py"
    if o.exists():
        assert o.read_bytes() == (ROOT / "n8hotspot" / "n8_admin.py").read_bytes()


def test_kit_files_loaded():
    html = (ROOT / "static" / "index.html").read_text()
    for f in ("/static/n8-kit.css", "/static/n8-kit.js", "/static/i18n-app.js", 'id="updateBanner"'):
        assert f in html
    assert "'Calibration': 'Kalibrierung'" in (ROOT / "static" / "i18n-app.js").read_text()
