import json
import types


def _make(load_plugin, tmp_path):
    p = load_plugin("field_notes.py", options={"data_path": str(tmp_path / "notes.json")})
    p.on_loaded()
    return p


def test_add_note_stamps_and_saves(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    rec = p.add_note("cool spot", lat=51.5, lon=-0.13, ts=1_700_000_000)
    assert rec["id"] == 1
    assert rec["text"] == "cool spot"
    assert rec["lat"] == 51.5 and rec["lon"] == -0.13
    assert "when" in rec
    saved = json.loads((tmp_path / "notes.json").read_text())
    assert len(saved) == 1 and saved[0]["text"] == "cool spot"


def test_add_note_ignores_empty(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.add_note("   ") is None
    assert p.add_note(None) is None
    assert p._notes == []


def test_ids_increment(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.add_note("a")
    r2 = p.add_note("b")
    assert r2["id"] == 2


def test_persist_across_instances(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.add_note("first")
    p2 = _make(load_plugin, tmp_path)
    assert len(p2._notes) == 1
    r = p2.add_note("second")
    assert r["id"] == 2


def test_webhook_get_adds_note(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    req = types.SimpleNamespace(method="GET", args={"note": "via-get"}, form={})
    # args/form need .get; SimpleNamespace dicts already have it
    body = p.on_webhook("/", req)
    assert "via-get" in body
    assert len(p._notes) == 1


def test_webhook_post_adds_note(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    req = types.SimpleNamespace(method="POST", form={"text": "via-post"}, args={})
    p.on_webhook("/", req)
    assert p._notes[-1]["text"] == "via-post"


def test_ui(load_plugin, ui, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.add_note("x")
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("field_notes") == "1"
    p.on_unload(ui)
    assert not ui.has_element("field_notes")


def test_missing_options_does_not_crash(load_plugin, ui, tmp_path):
    # No options at all: on_loaded applies defaults; load+UI must not raise. We redirect
    # the data path afterwards so the test never touches the real /etc default.
    p = load_plugin("field_notes.py")
    p.on_loaded()
    p._path = str(tmp_path / "n.json")
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("field_notes").isdigit()
    p.on_unload(ui)
