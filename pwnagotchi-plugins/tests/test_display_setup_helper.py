import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("display_setup_helper", ROOT / "display_setup_helper.py")
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)


def test_parse_config_overlays():
    text = ("# comment\n"
            "dtparam=spi=on\n"
            "dtoverlay=tft35a:rotate=90\n"
            "dtoverlay=gpio-fan\n")
    overlays, spi = ds.parse_config_overlays(text)
    assert overlays == ["tft35a:rotate=90", "gpio-fan"]
    assert spi is True


def test_parse_config_no_spi():
    _, spi = ds.parse_config_overlays("dtoverlay=tft35a\n")
    assert spi is False


def test_detect_panel():
    assert "tft35a" in ds.detect_panel(["tft35a:rotate=90"]).lower()
    assert "ili9486" in ds.detect_panel(["fb_ili9486"]).lower()
    assert "e-ink" in ds.detect_panel(["waveshare_epd"]).lower() or \
           "e-Paper" in ds.detect_panel(["waveshare_epd"])
    assert ds.detect_panel(["gpio-fan"]) is None


def test_parse_fb_devices(tmp_path):
    (tmp_path / "fb0").mkdir()
    (tmp_path / "fb0" / "virtual_size").write_text("1920,1080\n")
    (tmp_path / "fb1").mkdir()
    (tmp_path / "fb1" / "virtual_size").write_text("480,320\n")
    devs = ds.parse_fb_devices(str(tmp_path))
    assert devs == [{"name": "fb0", "size": "1920,1080"}, {"name": "fb1", "size": "480,320"}]


def test_suggest_working_tft():
    ev = {"overlays": ["tft35a:rotate=90"], "spi": True,
          "fbs": [{"name": "fb0", "size": "1920,1080"}, {"name": "fb1", "size": "480,320"}]}
    r = ds.suggest(ev)
    assert "3.5" in (r["panel"] or "")
    assert any("fb1" in f for f in r["findings"])
    assert r["config_lines"] == []            # nothing to change


def test_suggest_no_display():
    ev = {"overlays": ["gpio-fan"], "spi": False, "fbs": [{"name": "fb0", "size": "1920,1080"}]}
    r = ds.suggest(ev)
    assert r["panel"] is None
    assert "dtparam=spi=on" in r["config_lines"]
    assert any("dtoverlay" in line for line in r["config_lines"])


def test_suggest_overlay_but_no_fb():
    ev = {"overlays": ["tft35a"], "spi": True, "fbs": [{"name": "fb0", "size": "1920,1080"}]}
    r = ds.suggest(ev)
    assert r["panel"] is not None
    assert any("no TFT framebuffer" in f for f in r["findings"])


def test_analyze_and_ui(load_plugin, tmp_path, ui):
    cfg = tmp_path / "config.txt"
    cfg.write_text("dtparam=spi=on\ndtoverlay=tft35a:rotate=90\n")
    graphics = tmp_path / "graphics"
    (graphics / "fb0").mkdir(parents=True)
    (graphics / "fb0" / "virtual_size").write_text("1920,1080\n")
    (graphics / "fb1").mkdir()
    (graphics / "fb1" / "virtual_size").write_text("480,320\n")

    p = load_plugin("display_setup_helper.py", options={"config_path": str(cfg)})
    p.on_loaded()
    p._graphics = str(graphics)
    r = p.analyze()
    assert "3.5" in (r["panel"] or "")
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert "3.5" in ui.get("disp")
    p.on_unload(ui)
    assert not ui.has_element("disp")
