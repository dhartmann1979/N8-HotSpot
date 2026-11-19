import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot.db import DB  # noqa: E402
from n8hotspot.freeradioid import AVATAR_URL, IDS_URL, PROFILE_URL, FreeRadioID  # noqa: E402


def png(color):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (500, 500), color).save(b, "PNG")
    return b.getvalue()


PLACEHOLDER = png((128, 128, 128))
REG = json.dumps({"count": 2, "results": [
    {"id": 2621234, "callsign": "dl1abc", "fname": "Andreas", "city": "Minden", "state": 0, "country": "Germany"},
    {"id": 2627042, "callsign": "DB9NAC", "fname": "Nadine", "city": "Hannover", "state": "", "country": "Germany"}]}).encode()


class FakeNet:
    def __init__(self):
        self.calls = []

    def __call__(self, url, limit=0, timeout=0):
        self.calls.append(url)
        if url == IDS_URL:
            return REG
        if url == AVATAR_URL.format(id=0) or url == AVATAR_URL.format(id=2627042):
            return PLACEHOLDER                          # no own picture
        if url == AVATAR_URL.format(id=2621234):
            return png((200, 30, 30))
        if url == PROFILE_URL.format(id=2621234):
            return json.dumps({"reg": True, "results": [{"callsign": "DL1ABC", "fname": "Andreas", "surname": "M.",
                                                         "city": "Minden", "country": "Germany", "remarks": "N8"}]}).encode()
        raise OSError("offline")


def test_registered_avatars_profiles(tmp_path):
    net = FakeNet()
    f = FreeRadioID(DB(tmp_path / "t.db"), fetch=net)
    assert f.refresh_registered() == 2
    assert f.is_registered(2621234) and f.is_registered(262123401) and not f.is_registered(3100001)
    assert f.info(2621234)["callsign"] == "DL1ABC"
    assert f.avatar_id(262123401) == 2621234
    assert f.fetch_avatar(2621234) is True
    has, mime, data, _ = f.avatar(2621234)
    assert has and mime == "image/webp" and len(data) < 20000            # 500 px PNG -> 192 px WebP
    assert f.fetch_avatar(2627042) is False                              # grey placeholder = no picture
    assert not f.avatar_due(2621234) and f.avatar_stats() == {"with_avatar": 1, "without": 1}
    p = f.profile(262123401)
    assert p["name"] == "Andreas M." and p["registered"] and p["remarks"] == "N8"
    n = len(net.calls)
    f.profile(2621234)
    assert len(net.calls) == n                                           # cached
    assert f.profile(2627042)["city"] == "Hannover"                      # API down -> local list


def test_api_avatar_and_station(tmp_path, monkeypatch):
    monkeypatch.setenv("N8HS_DATA", str(tmp_path))
    import importlib
    import n8hotspot.app as appmod
    appmod = importlib.reload(appmod)
    monkeypatch.setattr(appmod.Live, "start_mqtt", lambda self, *a, **k: None)
    from fastapi.testclient import TestClient
    with TestClient(appmod.app) as c:
        net = FakeNet()
        appmod.ctx.frid.fetch = net
        appmod.ctx.frid.refresh_registered()
        r = c.get("/api/avatar/2621234")
        assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
        assert c.get("/api/avatar/3100001").status_code == 404           # not registered: FreeRadioID is not asked
        assert not any("3100001" in u for u in net.calls)
        appmod.ctx.db.x("INSERT INTO calls (ts, source, slot, src_id, callsign, dst_id, grp, duration) VALUES (strftime('%s','now'),'rf',2,2621234,'DL1ABC',262,1,7.5)")
        s = c.get("/api/station/2621234").json()
        assert s["frid"] and s["avatar"] == "/api/avatar/2621234" and s["heard"]["calls"] == 1
        assert s["talkgroups"][0]["tg"] == 262 and s["profile"]["name"] == "Andreas M."
        assert appmod.ctx.lookup(262123401)["frid"] is True
