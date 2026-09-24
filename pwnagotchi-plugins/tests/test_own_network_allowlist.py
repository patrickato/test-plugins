import json
import os


def _make(load_plugin, tmp_path, **opts):
    options = {
        "bssids": ["AA:BB:CC:DD:EE:FF"],
        "ssids": ["MyHomeWifi"],
        "data_path": str(tmp_path / "ledger.json"),
    }
    options.update(opts)
    plugin = load_plugin("own_network_allowlist.py", options=options)
    plugin.on_loaded()
    return plugin


def test_is_own_matches_mac_any_format(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.is_own({"mac": "aa-bb-cc-dd-ee-ff"})     # different separator/case
    assert p.is_own({"mac": "AABBCCDDEEFF"})
    assert not p.is_own({"mac": "11:22:33:44:55:66"})


def test_is_own_matches_ssid_case_insensitive(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert p.is_own({"mac": "00:00:00:00:00:01", "hostname": "myhomewifi"})
    assert not p.is_own({"mac": "00:00:00:00:00:01", "hostname": "CoffeeShop"})


def test_is_own_rejects_non_dict(load_plugin, tmp_path):
    p = _make(load_plugin, tmp_path)
    assert not p.is_own(None)
    assert not p.is_own("aa:bb:cc:dd:ee:ff")


def test_handshake_tags_own_capture(load_plugin, tmp_path, agent):
    p = _make(load_plugin, tmp_path)
    pcap = tmp_path / "cap.pcap"
    pcap.write_text("x")
    ap = {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "MyHomeWifi"}

    p.on_handshake(agent, str(pcap), ap, {"mac": "de:ad:be:ef:00:01"})

    assert (tmp_path / "cap.pcap.own").exists()          # sibling marker written
    ledger = json.loads((tmp_path / "ledger.json").read_text())
    assert len(ledger) == 1 and ledger[0]["mac"] == "aa:bb:cc:dd:ee:ff"


def test_handshake_ignores_foreign_capture(load_plugin, tmp_path, agent):
    p = _make(load_plugin, tmp_path)
    pcap = tmp_path / "foreign.pcap"
    pcap.write_text("x")
    p.on_handshake(agent, str(pcap), {"mac": "11:22:33:44:55:66", "hostname": "Neighbor"}, {})
    assert not (tmp_path / "foreign.pcap.own").exists()
    assert not (tmp_path / "ledger.json").exists()


def test_wifi_update_counts_in_range(load_plugin, tmp_path, agent, ui):
    p = _make(load_plugin, tmp_path)
    p.on_wifi_update(agent, [
        {"mac": "aa:bb:cc:dd:ee:ff"},          # own
        {"mac": "11:22:33:44:55:66"},          # foreign
        {"mac": "00:00:00:00:00:01", "hostname": "MyHomeWifi"},  # own by ssid
    ])
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("own_nets") == "2"


def test_survives_missing_options(load_plugin, agent, ui):
    plugin = load_plugin("own_network_allowlist.py")  # no options at all
    plugin.on_loaded()
    plugin.on_wifi_update(agent, [{"mac": "aa:bb:cc:dd:ee:ff"}])
    plugin.on_ui_setup(ui)
    plugin.on_ui_update(ui)
    assert ui.get("own_nets") == "0"
    plugin.on_unload(ui)
