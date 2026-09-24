import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("adsb_ambient", ROOT / "adsb_ambient.py")
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)


def test_parse_aircraft():
    obj = {"aircraft": [
        {"hex": "A1B2C3", "flight": "BAW123 ", "alt_baro": 30000, "rssi": -12.3},
        {"hex": "DDEEFF", "altitude": 12000},
        {"flight": "no-hex"},           # dropped: no hex
        "junk",
    ]}
    parsed = ad.parse_aircraft(obj)
    assert len(parsed) == 2
    assert parsed[0] == {"hex": "a1b2c3", "flight": "BAW123", "altitude": 30000, "rssi": -12.3}
    assert parsed[1]["altitude"] == 12000


def test_parse_aircraft_bad_input():
    assert ad.parse_aircraft(None) == []
    assert ad.parse_aircraft({}) == []


def _make(load_plugin, **opts):
    p = load_plugin("adsb_ambient.py", options=opts)
    p.on_loaded()
    return p


def test_update_tracks_current_and_distinct(load_plugin):
    p = _make(load_plugin)
    p.update([{"hex": "aaa"}, {"hex": "bbb"}], now=100)
    r = p.update([{"hex": "bbb"}, {"hex": "ccc"}], now=200)
    assert r == {"current": 2, "distinct": 3}   # aaa,bbb,ccc distinct; 2 overhead now


def test_update_respects_max_seen(load_plugin):
    p = _make(load_plugin, max_seen=1)
    p.update([{"hex": "a"}, {"hex": "b"}])
    assert len(p._seen) == 1


def test_ui(load_plugin, ui):
    p = _make(load_plugin)
    p.update([{"hex": "a"}, {"hex": "b"}])
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("adsb") == "2"
    p.on_unload(ui)
    assert not ui.has_element("adsb")


def test_ui_off_when_unreachable(load_plugin, ui):
    p = _make(load_plugin)
    p._reachable = False
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("adsb") == "off"
