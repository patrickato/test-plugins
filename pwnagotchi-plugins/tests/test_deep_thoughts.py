import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("deep_thoughts", ROOT / "deep_thoughts.py")
dt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dt)


def test_default_pack_nonempty():
    assert len(dt.DEFAULT_THOUGHTS) >= 10


def _make(load_plugin, **opts):
    p = load_plugin("deep_thoughts.py", options=opts)
    p.on_loaded()
    return p


def test_sequential_pick_cycles(load_plugin):
    p = _make(load_plugin, random=False)
    p._thoughts = ["a", "b", "c"]
    p._idx = 0
    assert [p._pick() for _ in range(4)] == ["a", "b", "c", "a"]


def test_random_pick_in_pack(load_plugin):
    p = _make(load_plugin, random=True)
    p._thoughts = ["a", "b", "c"]
    for _ in range(20):
        assert p._pick() in ("a", "b", "c")


def test_maybe_rotate_respects_interval(load_plugin):
    p = _make(load_plugin, random=False, interval_secs=30)
    p._thoughts = ["a", "b"]
    p._idx = 0
    p._current = "a"
    p._last_change = 0
    assert p.maybe_rotate(now=10) is False        # too soon
    assert p._current == "a"
    assert p.maybe_rotate(now=40) is True          # past interval
    assert p._current in ("a", "b")


def test_custom_pack_from_file(load_plugin, tmp_path):
    f = tmp_path / "pack.txt"
    f.write_text("# comment\nthought one\n\nthought two\n")
    p = _make(load_plugin, thoughts_file=str(f))
    assert p._thoughts == ["thought one", "thought two"]


def test_missing_file_falls_back_to_default(load_plugin, tmp_path):
    p = _make(load_plugin, thoughts_file=str(tmp_path / "nope.txt"))
    assert p._thoughts == dt.DEFAULT_THOUGHTS


def test_ui(load_plugin, ui):
    p = _make(load_plugin, random=False)
    p._thoughts = ["hello world"]
    p._current = "hello world"
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("deep_thoughts") == "hello world"
    p.on_unload(ui)
    assert not ui.has_element("deep_thoughts")
