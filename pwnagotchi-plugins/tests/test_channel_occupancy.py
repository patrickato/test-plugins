def _make(load_plugin, tmp_path):
    p = load_plugin("channel_occupancy.py",
                    options={"data_path": str(tmp_path / "chan.json")})
    p.on_loaded()
    return p


def test_record_counts_observations(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record([{"mac": "a", "channel": 6}, {"mac": "b", "channel": 6}, {"mac": "c", "channel": 1}])
    assert p._obs[6] == 2
    assert p._obs[1] == 1


def test_record_ignores_bad_entries(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record([{"mac": "a"}, {"channel": None}, "notadict", {"mac": "b", "channel": "x"}])
    assert p._obs == {}


def test_busiest_by_session_unique(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record([{"mac": "a", "channel": 11}, {"mac": "b", "channel": 11},
              {"mac": "a", "channel": 11},                      # dup mac, not double-counted
              {"mac": "c", "channel": 1}])
    ch, count = p.busiest()
    assert ch == 11 and count == 2


def test_persist_roundtrip(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record([{"mac": "a", "channel": 6}])
    p._save()
    p2 = _make(load_plugin, tmp_path)
    assert p2._obs[6] == 1


def test_ui_and_empty(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("chan") == "-"
    p.record([{"mac": "a", "channel": 6}])
    p.on_ui_update(ui)
    assert ui.get("chan") == "6(1)"
    p.on_unload(ui)
    assert not ui.has_element("chan")
