import importlib.util
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pet_quips", ROOT / "pet_quips.py")
pq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pq)


def test_default_packs_present():
    assert set(pq.DEFAULT_QUIPS) == {"handshake", "lonely", "bored", "excited"}
    assert all(pq.DEFAULT_QUIPS.values())


def _make(load_plugin, **opts):
    p = load_plugin("pet_quips.py", options=opts)
    p.on_loaded()
    return p


def test_quip_for_category(load_plugin):
    p = _make(load_plugin)
    for cat in ("handshake", "lonely", "bored", "excited"):
        assert p.quip_for(cat) in pq.DEFAULT_QUIPS[cat]
    assert p.quip_for("nonsense") == ""


def test_say_sets_current_and_window(load_plugin):
    p = _make(load_plugin, show_secs=6)
    text = p.say("handshake", now=100)
    assert text == p._current
    assert p.showing(now=104) is True
    assert p.showing(now=200) is False


def test_overrides(load_plugin):
    p = _make(load_plugin, quips={"handshake": ["custom!"]})
    assert p.quip_for("handshake") == "custom!"
    # non-overridden category keeps defaults
    assert p.quip_for("bored") in pq.DEFAULT_QUIPS["bored"]


def test_event_handlers(load_plugin, agent):
    p = _make(load_plugin)
    p.on_handshake(agent, "f", {}, {})
    assert p._current in pq.DEFAULT_QUIPS["handshake"]
    p.on_lonely(agent)
    assert p._current in pq.DEFAULT_QUIPS["lonely"]


def test_ui_shows_and_clears(load_plugin, ui):
    p = _make(load_plugin, quips={"handshake": ["gotcha!"]})
    p.on_ui_setup(ui)
    p.say("handshake")
    p._until = time.time() + 100
    p.on_ui_update(ui)
    assert ui.get("pet_quips") == "gotcha!"
    p._until = 0
    p.on_ui_update(ui)
    assert ui.get("pet_quips") == ""
    p.on_unload(ui)
    assert not ui.has_element("pet_quips")
