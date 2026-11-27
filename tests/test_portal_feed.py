"""📰 Portal feed for the adn-frn-server: only into the local network, encrypted with the sync key (n8hotspot/n8feed.py)."""
import secrets
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot import n8feed  # noqa: E402
from tests.test_api import client  # noqa: E402,F401  (fixture)

KEY = "h" * 32
H = {"X-N8": "1", "Content-Type": n8feed.CTYPE}


def req(key=KEY):
    return n8feed.seal({"path": n8feed.PATH, "ts": time.time(), "id": secrets.token_hex(8), "data": {}}, key)


def test_feed(client, monkeypatch):  # noqa: F811
    import n8hotspot.app as A
    assert client.post(n8feed.PATH, content=req(), headers=H).status_code == 404            # off
    A.ctx.settings.update({"dashboard.portal_feed": True, "dashboard.portal_key": KEY}, "t")
    monkeypatch.setattr(A, "ip_of", lambda conn: "192.168.79.150")                            # the portal in the LAN
    assert client.post(n8feed.PATH, content=req("x" * 32), headers=H).status_code == 403
    r = client.post(n8feed.PATH, content=req(), headers=H)
    assert r.status_code == 200, r.text
    d = n8feed.unseal(r.content, KEY)["data"]
    assert d["system"] == "hotspot" and [k["label"] for k in d["kpis"]][1] == "Calls today"
    monkeypatch.setattr(A, "ip_of", lambda conn: "8.8.8.8")                                   # from the internet: never
    r = client.post(n8feed.PATH, content=req(), headers=H)
    assert r.status_code == 403 and "local network" in r.json()["error"]


@pytest.mark.parametrize("ip,ok", [("192.168.1.2", True), ("10.0.0.1", True), ("127.0.0.1", True), ("::1", True),
                                   ("fd00::1", True), ("::ffff:192.168.1.5", True), ("8.8.8.8", False), ("2a00:1450::1", False), ("x", False)])
def test_is_local(ip, ok):
    assert n8feed.is_local(ip) is ok
