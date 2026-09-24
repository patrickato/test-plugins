import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("happy_thoughts", ROOT / "happy_thoughts.py")
ht = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ht)


def test_default_pack_nonempty():
    assert len(ht.DEFAULT_QUIPS) >= 10


def _make(load_plugin, **opts):
    p = load_plugin("happy_thoughts.py", options=opts)
    p.on_loaded()
    return p


def test_sequential_pick_cycles(load_plugin):
    p = _make(load_plugin, random=False)
    p._quips = ["x", "y"]
    p._idx = 0
    assert [p._pick() for _ in range(3)] == ["x", "y", "x"]


def test_maybe_rotate_respects_interval(load_plugin):
    p = _make(load_plugin, random=False, interval_secs=20)
    p._quips = ["x", "y"]
    p._idx = 0
    p._current = "x"
    p._last_change = 0
    assert p.maybe_rotate(now=5) is False
    assert p.maybe_rotate(now=25) is True


def test_custom_pack(load_plugin, tmp_path):
    f = tmp_path / "q.txt"
    f.write_text("joke one\n# skip\njoke two\n")
    p = _make(load_plugin, quips_file=str(f))
    assert p._quips == ["joke one", "joke two"]


def test_ui(load_plugin, ui):
    p = _make(load_plugin, random=False)
    p._quips = ["ha"]
    p._current = "ha"
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("happy_thoughts") == "ha"
    p.on_unload(ui)
    assert not ui.has_element("happy_thoughts")
