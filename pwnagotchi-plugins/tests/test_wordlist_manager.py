import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("wordlist_manager", ROOT / "wordlist_manager.py")
wm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wm)


def test_dedupe_lines_order_preserving():
    assert wm.dedupe_lines(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]
    assert wm.dedupe_lines([]) == []


def test_file_stats(tmp_path):
    f = tmp_path / "w.txt"
    f.write_text("a\nb\nc\n")
    st = wm.file_stats(str(f))
    assert st["lines"] == 3
    assert st["bytes"] == 6


def _make(load_plugin, tmp_path, **opts):
    options = {"wordlist_dir": str(tmp_path)}
    options.update(opts)
    p = load_plugin("wordlist_manager.py", options=options)
    p.on_loaded()
    return p


def test_list_wordlists(load_plugin, tmp_path):
    (tmp_path / "rockyou.txt").write_text("password\n123456\n")
    (tmp_path / "extra.lst").write_text("hunter2\n")
    (tmp_path / "ignore.md").write_text("not a wordlist\n")
    p = _make(load_plugin, tmp_path)
    names = {wl["name"] for wl in p.list_wordlists()}
    assert names == {"rockyou.txt", "extra.lst"}


def test_dedupe_file(load_plugin, tmp_path):
    f = tmp_path / "dupey.txt"
    f.write_text("a\nb\na\nc\nb\n")
    p = _make(load_plugin, tmp_path)
    removed = p.dedupe_file(str(f))
    assert removed == 2
    assert f.read_text().splitlines() == ["a", "b", "c"]


def test_merge(load_plugin, tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\n")
    (tmp_path / "b.txt").write_text("two\nthree\n")
    p = _make(load_plugin, tmp_path)
    out = tmp_path / "merged.txt"
    count = p.merge([str(tmp_path / "a.txt"), str(tmp_path / "b.txt")], str(out))
    assert count == 3
    assert out.read_text().splitlines() == ["one", "two", "three"]


def test_ui(load_plugin, tmp_path, ui):
    (tmp_path / "a.txt").write_text("x\n")
    (tmp_path / "b.txt").write_text("y\n")
    p = _make(load_plugin, tmp_path)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("wordlists") == "2"
    p.on_unload(ui)
    assert not ui.has_element("wordlists")


def test_empty_dir_safe(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.list_wordlists() == []
    assert p.dedupe_all() == {}
