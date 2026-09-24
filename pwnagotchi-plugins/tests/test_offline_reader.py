import importlib.util
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("offline_reader", ROOT / "offline_reader.py")
orr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orr)


def test_list_zims(tmp_path):
    (tmp_path / "wikipedia.zim").write_bytes(b"x")
    (tmp_path / "manuals.zim").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    zims = orr.list_zims(str(tmp_path))
    assert [Path(z).name for z in zims] == ["manuals.zim", "wikipedia.zim"]


def test_list_zims_missing_dir():
    assert orr.list_zims("/does/not/exist") == []


def _make(load_plugin, tmp_path):
    p = load_plugin("offline_reader.py", options={"zim_dir": str(tmp_path)})
    p.on_loaded()
    return p


def test_webhook_lists_files(load_plugin, tmp_path):
    (tmp_path / "wikipedia.zim").write_bytes(b"x")
    p = _make(load_plugin, tmp_path)
    body = p.on_webhook("/", None)
    assert "wikipedia.zim" in body
    # libzim not installed in the test env -> listing-only note
    assert "Install libzim" in body or "listing only" in body


def test_webhook_empty_library(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    body = p.on_webhook("/", None)
    assert "No .zim files" in body


def test_webhook_zim_without_libzim(load_plugin, tmp_path):
    (tmp_path / "wikipedia.zim").write_bytes(b"x")
    p = _make(load_plugin, tmp_path)
    req = types.SimpleNamespace(args={"zim": "wikipedia.zim"})
    body = p.on_webhook("/", req)
    assert "libzim not installed" in body


def test_ui(load_plugin, tmp_path, ui):
    (tmp_path / "a.zim").write_bytes(b"x")
    (tmp_path / "b.zim").write_bytes(b"x")
    p = _make(load_plugin, tmp_path)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("zim") == "2"
    p.on_unload(ui)
    assert not ui.has_element("zim")
