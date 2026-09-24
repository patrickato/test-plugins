import time


def _make(load_plugin, **opts):
    p = load_plugin("boot_post.py", options=opts)
    p.on_loaded()
    return p


def test_clock_check(load_plugin):
    p = _make(load_plugin)
    assert p.check_clock(now=time.time())["status"] == "ok"
    assert p.check_clock(now=0)["status"] == "fail"          # 1970 -> unset


def test_disk_check_pass_and_fail(load_plugin, tmp_path):
    p = _make(load_plugin, min_free_mb=1)
    assert p.check_disk(str(tmp_path))["status"] == "ok"
    p2 = _make(load_plugin, min_free_mb=10**12)              # absurd threshold
    assert p2.check_disk(str(tmp_path))["status"] == "fail"


def test_temp_check_uses_fake(load_plugin):
    # fake pwnagotchi.temperature() returns 48C
    assert _make(load_plugin, max_temp_c=80).check_temp()["status"] == "ok"
    assert _make(load_plugin, max_temp_c=40).check_temp()["status"] == "warn"


def test_handshakes_check(load_plugin, tmp_path):
    p = _make(load_plugin)
    assert p.check_handshakes(str(tmp_path))["status"] == "ok"
    assert p.check_handshakes(str(tmp_path / "does-not-exist"))["status"] == "warn"


def test_run_post_and_summary(load_plugin, tmp_path, agent, ui):
    p = _make(load_plugin, handshakes=str(tmp_path), min_free_mb=1, max_temp_c=80)
    p.on_ready(agent)
    assert p._ran
    assert len(p._results) == 5
    # summary is "ok_count/total"
    total = len(p._results)
    assert p.summary().endswith("/%d" % total)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("boot_post") == p.summary()
    p.on_unload(ui)
    assert not ui.has_element("boot_post")


def test_webhook_before_and_after(load_plugin, tmp_path, agent):
    p = _make(load_plugin, handshakes=str(tmp_path))
    assert "not run yet" in p.on_webhook("/", None)
    p.on_ready(agent)
    body = p.on_webhook("/", None)
    assert "Boot POST" in body and "clock" in body
