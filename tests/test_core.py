import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot import configgen, stats  # noqa: E402
from n8hotspot.auth import Auth, AuthError, DEFAULT_PASSWORD, DEFAULT_USER  # noqa: E402
from n8hotspot.calib import CalSession  # noqa: E402
from n8hotspot.db import DB  # noqa: E402
from n8hotspot.idlist import IdList, parse_csv  # noqa: E402
from n8hotspot.live import Live  # noqa: E402
from n8hotspot.settings import Settings, SettingsError, hotspot_id, parse_freq, tg_names  # noqa: E402


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "t.db")


# ---------------------------------------------------------------- auth
def test_factory_login_and_change(db):
    a = Auth(db)
    r = a.login(DEFAULT_USER, DEFAULT_PASSWORD)
    assert r["user"]["role"] == "admin" and r["user"]["default_pw"]
    u = a.session_user(r["token"])
    with pytest.raises(AuthError):
        a.change_own(u, DEFAULT_PASSWORD, DEFAULT_PASSWORD)           # same as factory
    out = a.change_own(u, DEFAULT_PASSWORD, "geheim123", "dl1abc")
    assert out["username"] == "dl1abc" and not out["default_pw"]
    assert a.session_user(r["token"]) is None                          # sessions ended
    with pytest.raises(AuthError):
        a.login(DEFAULT_USER, DEFAULT_PASSWORD)
    assert a.login("dl1abc", "geheim123")["user"]["username"] == "dl1abc"


def test_last_admin_and_throttle(db):
    a = Auth(db)
    me = a.session_user(a.login(DEFAULT_USER, DEFAULT_PASSWORD)["token"])
    with pytest.raises(AuthError):
        a.update(me, me["id"], {"role": "viewer"})
    v = a.create(me, "gast", "password1", "viewer")
    assert v["role"] == "viewer"
    for _ in range(5):
        with pytest.raises(AuthError):
            a.login("gast", "nope", ip="1.2.3.4")
    with pytest.raises(AuthError, match="Too many"):
        a.login("gast", "password1", ip="1.2.3.4")


# ---------------------------------------------------------------- settings + config files
def test_settings_and_ini(db, tmp_path):
    st = Settings(db)
    assert parse_freq("438,8") == 438800000 and parse_freq("438800000") == 438800000
    with pytest.raises(SettingsError):
        st.update({"station.dmr_id": "12"})
    with pytest.raises(SettingsError):
        st.update({"dmr.slot1": True})                          # simplex: no TS1
    st.update({"station.callsign": "dl1abc", "station.dmr_id": "2621234", "station.suffix": "07",
               "modem.rx_freq": "433.6125", "network.password": "geheim", "network.options": "TS2=262",
               "expert.mmdvm": "[Modem]\nTrace=1\n[Lock File]\nEnable=1"})
    s = st.all()
    assert s["station.callsign"] == "DL1ABC" and hotspot_id(s) == 262123407
    st.update({"network.password": ""})                         # empty = keep
    assert st.get("network.password") == "geheim"
    files = configgen.write_all(s, tmp_path)
    assert all(files.values())
    m = (tmp_path / "MMDVM-Host.ini").read_text()
    g = (tmp_path / "DMRGateway.ini").read_text()
    assert "Id=262123407" in m and "RXFrequency=433612500" in m and "TXFrequency=433612500" in m
    assert "Trace=1" in m and "Trace=0" not in m and "[Lock File]\nEnable=1" in m
    assert "Duplex=0" in m and "Slot1=0" in m
    assert "Address=dmr.die-n8schicht.de" in g and "Password=geheim" in g and "Options=TS2=262" in g
    assert g.count("PassAllTG=") == 2
    assert configgen.write_all(s, tmp_path) == {"MMDVM-Host.ini": False, "DMRGateway.ini": False}
    assert tg_names("262 = Deutschland\n# x\n91: World")[91] == "World"


# ---------------------------------------------------------------- live data
def test_live_calls_and_link(db):
    events = []
    live = Live(db, lambda i: {"callsign": "DL1ABC", "name": "Andreas"} if i == 2621234 else {})
    live.listeners.append(events.append)
    live.handle("dmr-gateway/json", json.dumps({"status": {"message": "Opening DMR Network: N8schicht"}}))
    assert live.link["state"] == "connecting"
    live.handle("dmr-gateway/json", json.dumps({"link": {"action": "failed", "network": "N8schicht", "reason": "auth"}}))
    live.handle("dmr-gateway/json", json.dumps({"status": {"message": "Opening DMR Network: N8schicht"}}))
    assert live.link["state"] == "failed" and live.link["reason"] == "auth"
    live.handle("dmr-gateway/json", json.dumps({"link": {"action": "linking", "network": "N8schicht", "reason": "network"}}))
    assert live.link["state"] == "connected"
    live.handle("mmdvm/json", json.dumps({"MMDVM": {"mode": "dmr"}}))
    assert live.mode == "DMR"
    live.handle("mmdvm/json", json.dumps({"DMR": {"source": "rf", "action": "start", "slot": 2, "src_id": 2621234,
                                                  "dst_id": 262, "group": "yes", "src_info": "2621234"}}))
    assert live.slots[2]["callsign"] == "DL1ABC"
    live.handle("mmdvm/json", json.dumps({"BER": {"mode": "DMR", "slot": 2, "value": 0.4}}))
    live.handle("mmdvm/json", json.dumps({"DMR": {"action": "end", "slot": 2, "duration": 4.2, "ber": 0.3,
                                                  "rssi": {"min": -70, "max": -60, "ave": -64}}}))
    assert live.slots[2] is None
    e = live.last_heard[0]
    assert (e["source"], e["dst_id"], e["duration"], e["ber"], e["rssi"], e["name"]) == ("rf", 262, 4.2, 0.3, -64, "Andreas")
    # network call without end: a new start on the slot closes it as lost
    live.handle("mmdvm/json", json.dumps({"DMR": {"source": "network", "action": "start", "slot": 2, "src_id": 1, "dst_id": 91, "group": "yes", "src_info": "G4KLX"}}))
    live.handle("mmdvm/json", json.dumps({"DMR": {"source": "network", "action": "start", "slot": 2, "src_id": 2, "dst_id": 91, "group": "yes", "src_info": "M0ABC"}}))
    assert live.last_heard[0]["result"] == "lost" and live.slots[2]["callsign"] == "M0ABC"
    live.handle("mmdvm/log", "M: 2026-11-19 06:08:15.402 DMR Slot 2, received network voice header from M0ABC to TG 91")
    assert live.logs[-1]["level"] == "message"
    assert any(ev["type"] == "heard" for ev in events)


def test_modem_state_after_web_restart(db):
    """Nach einem Update startet die Weboberfläche neu, MMDVMHost läuft weiter – „Modem geöffnet“ kam schon vorher."""
    live = Live(db, lambda i: {})
    assert live.modem["open"] is None
    # aus dem Journal des laufenden MMDVMHost nachgeholt
    assert live.modem_from_journal(["M: 2026-11-25 Opening the MMDVM",
                                    "I: 2026-11-25 MMDVM protocol version: 1, description: MMDVM_HS_Hat-v1.6.1 20231115 FW by CA6JAU"])
    assert live.modem["open"] is True and live.modem["description"].startswith("MMDVM_HS_Hat")
    live2 = Live(db, lambda i: {})
    assert live2.modem_from_journal(["E: 2026-11-25 Unable to read the firmware version after six attempts"])
    assert live2.modem["open"] is False
    assert not Live(db, lambda i: {}).modem_from_journal(["M: something else"])
    # aus dem Betriebszustand / Funkempfang abgeleitet
    live3 = Live(db, lambda i: {})
    live3.handle("mmdvm/json", json.dumps({"MMDVM": {"mode": "idle"}}))
    assert live3.modem["open"] is True
    live4 = Live(db, lambda i: {})
    live4.handle("mmdvm/json", json.dumps({"DMR": {"action": "start", "slot": 2, "source": "rf", "src_id": 1, "dst_id": 9}}))
    assert live4.modem["open"] is True
    # die echte Meldung von MMDVMHost gewinnt
    live3.handle("mmdvm/json", json.dumps({"Modem": {"open": False}}))
    assert live3.modem["open"] is False


def test_stats(db):
    now = time.time()
    rows = [(now - 60, "rf", 262, 10.0), (now - 120, "network", 262, 5.0), (now - 180, "network", 91, 3.0)]
    db.many("INSERT INTO calls (ts, source, slot, src_id, callsign, dst_id, grp, duration) VALUES (?,?,2,1,'X',?,1,?)", rows)
    d = stats.summary(db, "24h", {262: "DE"})
    assert d["totals"]["calls"] == 3 and d["totals"]["rf_calls"] == 1 and d["talkgroups"][0]["name"] == "DE"
    assert sum(d["sources"][0]["calls"]) == 1 and len(d["buckets"]) == 24


def test_idlist(db, tmp_path):
    body = b"2621234,DL1ABC,Andreas,Berlin,,Germany\n" + b"".join(f"{3100000+i},K{i}AA,Bob,,,United States\n".encode() for i in range(20))
    ids = IdList(db, tmp_path)
    assert ids.load_bytes(body) == 21
    assert ids.lookup(2621234)["name"] == "Andreas"
    assert ids.lookup(262123401)["callsign"] == "DL1ABC"          # hotspot suffix
    assert (tmp_path / "DMRIds.dat").read_text().startswith("2621234\tDL1ABC\tAndreas")
    assert list(parse_csv(b"RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n1234567,DB0X,Rep,,,,Germany\n"))[0][1] == "DB0X"


# ---------------------------------------------------------------- calibration with the stand-in program
def test_calibration_fake():
    async def run():
        events = []
        cal = CalSession(f"{sys.executable} {ROOT / 'tools' / 'fake_mmdvmcal.py'}", events.append)
        await cal.start("/dev/null", 115200, 438800000)
        await cal.key("b")
        await asyncio.sleep(1.2)
        s = cal.snapshot()
        assert s["running"] and s["mode"].startswith("BER Test Mode") and s["ber"] is not None
        for _ in range(7):
            await cal.key("f")
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.8)
        assert cal.snapshot()["offset"] == -350
        await cal.stop()
        assert not cal.snapshot()["running"]
    asyncio.run(run())
