import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("signal_compass", ROOT / "signal_compass.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


def test_classify_proximity():
    assert sc.classify_proximity(-40) == "very close"
    assert sc.classify_proximity(-55) == "close"
    assert sc.classify_proximity(-70) == "near"
    assert sc.classify_proximity(-80) == "far"
    assert sc.classify_proximity(-90) == "very far"


def test_trend_from():
    assert sc.trend_from([-80, -78, -70, -60]) == "warmer"   # rising RSSI
    assert sc.trend_from([-50, -55, -70, -80]) == "colder"
    assert sc.trend_from([-60, -61, -60, -59]) == "steady"
    assert sc.trend_from([-60]) == "steady"                   # too few


def _make(load_plugin, **opts):
    p = load_plugin("signal_compass.py", options=opts)
    p.on_loaded()
    return p


def test_tracks_configured_target(load_plugin):
    p = _make(load_plugin, target="AA:BB:CC:DD:EE:FF", window=8)
    p.record([{"mac": "aabbccddeeff", "rssi": -70}, {"mac": "112233445566", "rssi": -40}])
    assert p._samples == [-70]           # only the target's rssi recorded
    st = p.status()
    assert st["rssi"] == -70 and st["proximity"] == "near"


def test_auto_strongest_locks_target(load_plugin):
    p = _make(load_plugin, auto_strongest=True)
    p.record([{"mac": "aaaaaaaaaaaa", "rssi": -80}, {"mac": "bbbbbbbbbbbb", "rssi": -50}])
    assert p._target == "bbbbbbbbbbbb"   # strongest
    assert p._samples == [-50]


def test_warmer_over_scans(load_plugin):
    p = _make(load_plugin, target="aaaaaaaaaaaa")
    for r in (-85, -82, -75, -65):
        p.record([{"mac": "aaaaaaaaaaaa", "rssi": r}])
    assert p.status()["trend"] == "warmer"


def test_window_caps_samples(load_plugin):
    p = _make(load_plugin, target="aaaaaaaaaaaa", window=3)
    for r in (-80, -78, -76, -74, -72):
        p.record([{"mac": "aaaaaaaaaaaa", "rssi": r}])
    assert len(p._samples) == 3 and p._samples[-1] == -72


def test_ui(load_plugin, ui):
    p = _make(load_plugin, target="aaaaaaaaaaaa")
    p.record([{"mac": "aaaaaaaaaaaa", "rssi": -58}])
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("sigcompass") == "=-58"     # single sample -> steady
    p.on_unload(ui)
    assert not ui.has_element("sigcompass")
