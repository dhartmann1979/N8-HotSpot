import os
import pty
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from n8hotspot import serialscan  # noqa: E402
from n8hotspot.db import DB  # noqa: E402
from n8hotspot.talkgroups import BUNDLED, Talkgroups, parse  # noqa: E402


def test_talkgroup_list(tmp_path):
    names = parse(BUNDLED.read_bytes())
    assert len(names) > 1000 and names[262] == "DEUTSCHLAND NATIONAL"
    assert names[2627] == "BADEN-WÜRTTEMBERG"                     # mojibake repaired
    assert 3 not in names                                         # "N/A" dropped
    raw = '{"results":[{"TG-id":"9","callsign":"DIAL-a-TG","id":"9"},{"TG-id":"2021","callsign":"2021","id":"2021"}]}'
    assert parse(raw.encode()) == {9: "DIAL-a-TG"}
    t = Talkgroups(DB(tmp_path / "t.db"))
    assert t.count() == len(names)                                # bundled copy on the first start


def test_modem_probe_and_version():
    m, s = pty.openpty()
    path = os.ttyname(s)

    def modem():
        buf = b""
        while True:
            try:
                buf += os.read(m, 64)
            except OSError:
                return
            if b"\xe0\x03\x00" in buf:
                body = bytes([0x00, 1]) + b"MMDVM_HS_Dual_Hat-v1.6.1 20230805\x00ABCD"
                os.write(m, bytes([0xE0, len(body) + 2]) + body)
                buf = b""
    threading.Thread(target=modem, daemon=True).start()
    info = serialscan.probe(path, 115200)
    assert info == {"protocol": 1, "description": "MMDVM_HS_Dual_Hat-v1.6.1 20230805"}
    v2 = bytes([0x00, 2, 0x6F, 0x01, 2]) + bytes(16) + b"ZUMspot-v1.6.1"
    assert serialscan.parse_version(bytes([0xE0, len(v2) + 2]) + v2) == {"protocol": 2, "cpu": "ST-Micro ARM", "description": "ZUMspot-v1.6.1"}
    assert serialscan.parse_version(b"\xe0\x04\x7f\x01") is None
