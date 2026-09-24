import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("circadian_faces", ROOT / "circadian_faces.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)


def test_sun_times_london_midsummer():
    sun = cf.compute_sun_times(2026, 6, 21, 51.5, -0.13)
    assert isinstance(sun, tuple)
    rise, sset = sun
    # London ~03:43 UTC sunrise, ~20:21 UTC sunset in late June.
    assert 3.0 < rise < 5.0
    assert 19.5 < sset < 21.0
    assert rise < sset


def test_sun_times_polar():
    assert cf.compute_sun_times(2026, 6, 21, 80.0, 0.0) == "polar-day"
    assert cf.compute_sun_times(2026, 12, 21, 80.0, 0.0) == "polar-night"


def test_phase_from_sun_windows():
    sun = (6.0, 18.0)          # sunrise 06:00, sunset 18:00 UTC
    m = 0.5                     # 30-min margin
    assert cf.phase_from_sun(3.0, sun, m) == "night"
    assert cf.phase_from_sun(6.0, sun, m) == "dawn"
    assert cf.phase_from_sun(12.0, sun, m) == "day"
    assert cf.phase_from_sun(18.0, sun, m) == "dusk"
    assert cf.phase_from_sun(22.0, sun, m) == "night"
    assert cf.phase_from_sun(0.0, "polar-night", m) == "night"
    assert cf.phase_from_sun(0.0, "polar-day", m) == "day"


def test_phase_from_schedule():
    assert cf.phase_from_schedule(12, 7, 20) == "day"
    assert cf.phase_from_schedule(23, 7, 20) == "night"
    assert cf.phase_from_schedule(6, 7, 20) == "night"


def test_face_mapping_and_override(load_plugin, ui):
    p = load_plugin("circadian_faces.py", options={
        "day_start": 7, "night_start": 20, "faces": {"day": "DAYFACE", "night": "NIGHTFACE"}})
    p.on_loaded()
    assert p.face_for("day") == "DAYFACE"
    assert p.face_for("night") == "NIGHTFACE"
    # override sets the 'face' state to a valid phase face
    p.on_ui_update(ui)
    assert ui.get("face") in ("DAYFACE", "NIGHTFACE")


def test_no_override_leaves_face_untouched(load_plugin, ui):
    p = load_plugin("circadian_faces.py", options={"override_face": False})
    p.on_loaded()
    p.on_ui_update(ui)
    assert ui.get("face") is None
