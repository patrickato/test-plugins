import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("eink_ghosting", ROOT / "eink_ghosting.py")
eg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eg)


def test_should_full_refresh():
    assert eg.should_full_refresh(60, 0, 60, 600) is True      # partial budget hit
    assert eg.should_full_refresh(0, 700, 60, 600) is True     # time budget hit
    assert eg.should_full_refresh(10, 100, 60, 600) is False   # neither
    assert eg.should_full_refresh(100, 0, 0, 600) is False     # partials disabled (0)


def _make(load_plugin, **opts):
    p = load_plugin("eink_ghosting.py", options=opts)
    p.on_loaded()
    p._refresh_fn = lambda: p.__dict__.__setitem__("_did_refresh",
                                                   p.__dict__.get("_did_refresh", 0) + 1)
    return p


def test_partial_budget_triggers_refresh(load_plugin):
    p = _make(load_plugin, max_partials=5, max_interval_s=100000)
    for _ in range(4):
        p.note_partial()
    assert p.maybe_refresh(now=0) is False      # only 4 partials
    p.note_partial()                             # now 5
    assert p.maybe_refresh(now=1) is True
    assert p._did_refresh == 1
    assert p._partials == 0                       # counter reset
    assert p._fulls == 1


def test_time_budget_triggers_refresh(load_plugin):
    p = _make(load_plugin, max_partials=100000, max_interval_s=600)
    p._last_full = 0
    assert p.maybe_refresh(now=599) is False
    assert p.maybe_refresh(now=600) is True
    assert p._did_refresh == 1


def test_ui_counts_partials(load_plugin, ui):
    p = _make(load_plugin, show_counter=True)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    p.on_ui_update(ui)
    assert ui.get("eink") == "2"
    p.on_unload(ui)
    assert not ui.has_element("eink")


def test_no_counter_element_when_disabled(load_plugin, ui):
    p = _make(load_plugin, show_counter=False)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert not ui.has_element("eink")            # no element, but partial still counted
    assert p._partials == 1
