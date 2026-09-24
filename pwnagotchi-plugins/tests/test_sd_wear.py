import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sd_wear", ROOT / "sd_wear.py")
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)


def test_strip_partition():
    assert sw.strip_partition("/dev/mmcblk0p2") == "mmcblk0"
    assert sw.strip_partition("/dev/nvme0n1p2") == "nvme0n1"
    assert sw.strip_partition("/dev/sda2") == "sda"
    assert sw.strip_partition("/dev/mmcblk0") == "mmcblk0"


def test_root_device_from_mounts():
    mounts = ("proc /proc proc rw 0 0\n"
              "/dev/mmcblk0p2 / ext4 rw 0 0\n"
              "/dev/mmcblk0p1 /boot vfat rw 0 0\n")
    assert sw.root_device_from_mounts(mounts) == "mmcblk0"


def test_parse_diskstats():
    line = " 179       0 mmcblk0 1000 0 5000 100 2000 0 8000 200 0 100 300"
    assert sw.parse_diskstats(line, "mmcblk0") == 8000     # field index 9 = sectors written
    assert sw.parse_diskstats(line, "sda") is None


def test_estimate():
    rated = 30e12
    est = sw.estimate(15e12, 86400 * 10, rated)   # 15 TB in 10 days
    assert abs(est["pct"] - 50.0) < 0.01
    assert abs(est["rate_gb_per_day"] - 1500.0) < 1     # 15TB/10d = 1.5TB/day
    # remaining 15TB at 1.5TB/day -> ~10 days
    assert abs(est["projected_days"] - 10.0) < 0.1


def _make(load_plugin, tmp_path, **opts):
    options = {"device": "mmcblk0", "data_path": str(tmp_path / "sd.json"), "rated_tbw": 30}
    options.update(opts)
    p = load_plugin("sd_wear.py", options=options)
    p.on_loaded()
    return p


def test_update_accumulates(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.update(1000, now=0) == 0            # first sample: baseline only
    p.update(3000, now=10)                        # +2000 sectors
    assert p._cumulative == 2000 * sw.SECTOR


def test_update_handles_reboot_reset(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.update(10000, now=0)                         # baseline
    p.update(12000, now=10)                        # +2000
    p.update(500, now=20)                          # counter reset -> count 500 fresh
    assert p._cumulative == (2000 + 500) * sw.SECTOR


def test_ui(load_plugin, tmp_path, ui):
    p = _make(load_plugin, tmp_path)
    p._cumulative = 12e9          # 12 GB
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("sd_wear") == "12G"
    p.on_unload(ui)
    assert not ui.has_element("sd_wear")


def test_persist_roundtrip(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    p.update(1000, now=0)
    p.update(5000, now=10)
    p._save()
    p2 = _make(load_plugin, tmp_path)
    assert p2._cumulative == 4000 * sw.SECTOR
