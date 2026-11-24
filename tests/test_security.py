"""Hardening (N8 security), N8 update guard and N8 Kit files."""
import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot import n8_security, n8_update_guard as guard  # noqa: E402


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


def _repo(tmp_path):
    r = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    g = ["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(g + ["commit", "-q", "--allow-empty", "-m", "a"], check=True)
    old = subprocess.check_output(["git", "-C", str(r), "rev-parse", "HEAD"], text=True).strip()
    (r / "f").write_text("x")
    subprocess.run(["git", "-C", str(r), "add", "f"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "b"], check=True)
    new = subprocess.check_output(["git", "-C", str(r), "rev-parse", "HEAD"], text=True).strip()
    return r, old, new


def test_guard_rolls_back_after_three_starts(tmp_path):
    r, old, new = _repo(tmp_path)
    st = tmp_path / "state"
    guard.mark_pending(st, old, new, "v1.3.0 · a", "v1.4.0 · b")
    for _ in range(4):
        subprocess.run(["sh", str(ROOT / "scripts" / "n8-update-guard.sh"), str(r), str(st)], check=True, capture_output=True)
    assert subprocess.check_output(["git", "-C", str(r), "rev-parse", "HEAD"], text=True).strip() == old
    res = guard.last_result(st)
    assert res["ok"] is False and res["to"] == "v1.4.0 · b" and not guard.pending(st)


def test_guard_confirms_when_web_answers(tmp_path):
    import http.server
    import threading
    srv = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        guard.mark_pending(tmp_path, "a" * 40, "b" * 40)
        res = asyncio.run(guard.startup_check(tmp_path, guard.local_url("0.0.0.0", srv.server_port), timeout=10, delay=0))
        assert res["ok"] and not guard.pending(tmp_path)
    finally:
        srv.shutdown()


def test_unit_uses_the_guard():
    unit = (ROOT / "systemd" / "n8hotspot.service").read_text()
    assert "ExecStartPre=-/bin/sh /opt/n8hotspot/scripts/n8-update-guard.sh /opt/n8hotspot /opt/n8hotspot/data" in unit


def test_kit_files_loaded():
    html = (ROOT / "static" / "index.html").read_text()
    for f in ("/static/n8-kit.css", "/static/n8-kit.js", "/static/i18n-app.js", 'id="updateBanner"'):
        assert f in html
    assert "'Calibration': 'Kalibrierung'" in (ROOT / "static" / "i18n-app.js").read_text()
