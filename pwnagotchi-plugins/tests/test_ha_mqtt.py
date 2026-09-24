import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ha_mqtt", ROOT / "ha_mqtt.py")
hm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hm)


def test_state_topic():
    assert hm.state_topic_for("homeassistant", "pwny") == "homeassistant/sensor/pwny/state"


def test_build_discovery_configs():
    cfgs = hm.build_discovery_configs("pwny", "homeassistant")
    # one config topic per sensor
    assert len(cfgs) == len(hm.SENSORS)
    temp_topic = "homeassistant/sensor/pwny/temperature/config"
    assert temp_topic in cfgs
    payload = cfgs[temp_topic]
    assert payload["state_topic"] == "homeassistant/sensor/pwny/state"
    assert payload["unique_id"] == "pwny_temperature"
    assert payload["value_template"] == "{{ value_json.temperature }}"
    assert payload["unit_of_measurement"] == "°C"
    assert payload["device"]["identifiers"] == ["pwny"]


def _make(load_plugin, **opts):
    p = load_plugin("ha_mqtt.py", options=opts)
    p.on_loaded()
    return p


def test_gather_values_uses_fakes(load_plugin):
    p = _make(load_plugin)
    p._handshakes = 3
    vals = p.gather_values()
    # fake pwnagotchi: temp 48, cpu 0.17, mem 0.42, uptime 12345
    assert vals["temperature"] == 48.0
    assert vals["cpu"] == 17.0
    assert vals["memory"] == 42.0
    assert vals["uptime"] == 12345
    assert vals["handshakes"] == 3


def test_handshake_increments(load_plugin, agent):
    p = _make(load_plugin)
    p.on_handshake(agent, "f.pcap", {}, {})
    p.on_handshake(agent, "g.pcap", {}, {})
    assert p._handshakes == 2


def test_ui_reflects_connection(load_plugin, ui):
    p = _make(load_plugin)
    p.on_ui_setup(ui)
    p.on_ui_update(ui)
    assert ui.get("hamqtt") == "off"
    p._connected = True
    p.on_ui_update(ui)
    assert ui.get("hamqtt") == "on"
    p.on_unload(ui)
    assert not ui.has_element("hamqtt")
