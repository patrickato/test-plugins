def _make(load_plugin, tmp_path):
    p = load_plugin("streaks.py", options={"data_path": str(tmp_path / "streaks.json")})
    p.on_loaded()
    return p


def test_first_day(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_activity(today="2026-01-01")
    assert p._state["days_alive"] == 1
    assert p._state["current_streak"] == 1
    assert p._state["first_seen"] == "2026-01-01"


def test_consecutive_days_build_streak(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    for d in ("2026-01-01", "2026-01-02", "2026-01-03"):
        p.record_activity(today=d)
    assert p._state["days_alive"] == 3
    assert p._state["current_streak"] == 3
    assert p._state["longest_streak"] == 3


def test_gap_resets_streak_but_keeps_longest(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    for d in ("2026-01-01", "2026-01-02"):   # streak 2
        p.record_activity(today=d)
    p.record_activity(today="2026-01-10")    # gap -> streak resets
    assert p._state["current_streak"] == 1
    assert p._state["longest_streak"] == 2
    assert p._state["days_alive"] == 3


def test_same_day_is_not_double_counted(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_activity(today="2026-01-01")
    p.record_activity(today="2026-01-01")
    assert p._state["days_alive"] == 1


def test_daily_network_and_handshake_records(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_networks([{"mac": "a"}, {"mac": "b"}, {"mac": "a"}], today="2026-01-01")
    assert p._state["networks_today"] == 2
    p.record_networks([{"mac": "x"}, {"mac": "y"}, {"mac": "z"}], today="2026-01-02")
    assert p._state["most_networks_in_a_day"] == 3   # day 2 beat day 1
    assert p._state["networks_today"] == 3           # counter reset on the new day

    p.record_handshake(today="2026-01-02")
    p.record_handshake(today="2026-01-02")
    assert p._state["most_handshakes_in_a_day"] == 2


def test_state_persists_across_instances(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.record_activity(today="2026-01-01")
    p.record_activity(today="2026-01-02")

    p2 = _make(load_plugin, tmp_path)                # fresh instance, same file
    p2.record_activity(today="2026-01-03")
    assert p2._state["current_streak"] == 3
    assert p2._state["days_alive"] == 3


def test_ui_and_missing_options(load_plugin, ui):
    p = load_plugin("streaks.py")   # no data_path
    p.on_loaded()
    p.record_activity(today="2026-01-01")
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("streaks") == "1d 1s"
    p.on_unload(ui)
    assert not ui.has_element("streaks")
