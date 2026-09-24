import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("daily_digest", ROOT / "daily_digest.py")
dd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dd)


def _make(load_plugin, tmp_path, **opts):
    options = {"digest_dir": str(tmp_path / "digests"),
               "data_path": str(tmp_path / "dd.json")}
    options.update(opts)
    p = load_plugin("daily_digest.py", options=options)
    p.on_loaded()
    return p


def test_record_accumulates(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(today="2026-01-01")
    p.record_handshake(today="2026-01-01")
    p.record_networks([{"mac": "a"}, {"mac": "b"}, {"mac": "a"}], today="2026-01-01")
    assert p._handshakes == 2
    assert len(p._networks) == 2


def test_rollover_writes_card_and_resets(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(today="2026-01-01")
    p.record_networks([{"mac": "a"}], today="2026-01-01")
    # crossing into a new day finalizes the previous one
    result = p.maybe_rollover(today="2026-01-02")
    assert result is not None
    summary, path = result
    assert summary["handshakes"] == 1 and summary["networks"] == 1
    assert Path(path).exists()
    assert Path(path).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"   # valid PNG header
    # counters reset for the new day
    assert p._handshakes == 0 and p._networks == set() and p._day == "2026-01-02"


def test_no_rollover_same_day(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(today="2026-01-01")
    assert p.maybe_rollover(today="2026-01-01") is None


def test_render_card_directly(tmp_path):
    out = tmp_path / "card.png"
    path = dd.render_card({"date": "2026-01-01", "handshakes": 5, "networks": 12, "uptime": 999},
                          str(out))
    assert path == str(out)
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_persist_roundtrip(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(today="2026-01-01")
    p.record_networks([{"mac": "a"}], today="2026-01-01")
    p2 = _make(load_plugin, tmp_path)
    assert p2._handshakes == 1 and p2._day == "2026-01-01" and p2._networks == {"a"}


def test_ui(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p.record_handshake(today="2026-01-01")
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("digest") == "1"
    p.on_unload(ui)
    assert not ui.has_element("digest")
