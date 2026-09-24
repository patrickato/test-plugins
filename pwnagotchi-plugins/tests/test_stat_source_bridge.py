import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("stat_source_bridge", ROOT / "stat_source_bridge.py")
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)


def test_build_bridge_prefers_our_value():
    vf = lambda k: "42" if k == "pwn_x" else None
    prior = lambda k: "PRIOR" if k == "y" else None
    b = sb.build_bridge(vf, prior)
    assert b("pwn_x") == "42"        # ours
    assert b("y") == "PRIOR"          # delegated
    assert b("z") is None             # neither
    assert b._is_bridge is True


def test_build_bridge_no_prior():
    b = sb.build_bridge(lambda k: None, None)
    assert b("anything") is None


def _make(load_plugin, **opts):
    p = load_plugin("stat_source_bridge.py", options=opts)
    p.on_loaded()
    return p


def test_value_for_uses_fakes(load_plugin):
    p = _make(load_plugin, prefix="pwn_")
    # fake pwnagotchi: temp 48, cpu 0.17, mem 0.42
    assert p.value_for("pwn_temp") == "48C"
    assert p.value_for("pwn_cpu") == "17%"
    assert p.value_for("pwn_mem") == "42%"
    assert p.value_for("pwn_handshakes") == "0"
    assert p.value_for("pwn_unknown") is None     # not in keys
    assert p.value_for("othertoken") is None       # wrong prefix


def test_value_for_respects_keys(load_plugin):
    p = _make(load_plugin, keys=["temp"])
    assert p.value_for("pwn_temp") == "48C"
    assert p.value_for("pwn_cpu") is None          # cpu not exposed


def test_handshake_increments(load_plugin, agent):
    p = _make(load_plugin)
    p.on_handshake(agent, "f", {}, {})
    assert p.value_for("pwn_handshakes") == "1"


def test_install_into_fake_theme_manager(load_plugin, agent):
    # Simulate Theme Manager already loaded, with its own STAT_SOURCE (_live_stat).
    fake_tm = types.ModuleType("theme_manager")
    fake_tm._Lazy = dict
    fake_tm.STAT_SOURCE = lambda key: "TM" if key == "session" else None
    sys.modules["theme_manager"] = fake_tm
    try:
        p = _make(load_plugin)
        assert p.install() is True
        assert getattr(fake_tm.STAT_SOURCE, "_is_bridge", False) is True
        # our token resolves, and Theme Manager's own key still delegates through
        assert fake_tm.STAT_SOURCE("pwn_temp") == "48C"
        assert fake_tm.STAT_SOURCE("session") == "TM"
        assert fake_tm.STAT_SOURCE("nope") is None
        # idempotent: installing again doesn't double-wrap
        first = fake_tm.STAT_SOURCE
        p.install()
        assert fake_tm.STAT_SOURCE is first
    finally:
        del sys.modules["theme_manager"]


def test_install_noop_without_theme_manager(load_plugin, ui):
    p = _make(load_plugin)
    # no module with STAT_SOURCE+_Lazy present -> guarded no-op
    assert p.install() is False
    assert p._installed is False
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("bridge") == "off"
    p.on_unload(ui)
    assert not ui.has_element("bridge")
