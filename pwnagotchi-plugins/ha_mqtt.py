"""ha_mqtt — publish Pwnagotchi state to Home Assistant via MQTT discovery.

Widely wanted, no clean plugin. This auto-registers a handful of sensors (temperature, CPU,
memory, uptime, session handshakes) with Home Assistant using MQTT discovery, then publishes
their values on an interval. HA picks up the device automatically — no manual sensor config.

Guarded: if ``paho-mqtt`` isn't installed or the broker is unreachable, the plugin idles.

Options (main.plugins.ha_mqtt.*):
    enabled     = true
    host        = "127.0.0.1"
    port        = 1883
    username    =
    password    =
    base_topic  = "homeassistant"
    node_id     =              # defaults to the hostname
    interval    = 30           # seconds between state publishes
    position    = "0,0"

Requires: pip `paho-mqtt`, and a reachable MQTT broker (e.g. the one Home Assistant uses).
"""
import json
import logging
import socket
import time

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

# key, friendly name, unit, HA device_class (or None)
SENSORS = [
    ("temperature", "Temperature", "°C", "temperature"),
    ("cpu", "CPU", "%", None),
    ("memory", "Memory", "%", None),
    ("uptime", "Uptime", "s", "duration"),
    ("handshakes", "Handshakes", None, None),
]


def state_topic_for(base_topic, node_id):
    return "%s/sensor/%s/state" % (base_topic, node_id)


def build_discovery_configs(node_id, base_topic, sensors=SENSORS):
    """Return {config_topic: payload_dict} for HA MQTT discovery."""
    state_topic = state_topic_for(base_topic, node_id)
    device = {"identifiers": [node_id], "name": node_id,
              "model": "Pwnagotchi", "manufacturer": "pwnagotchi"}
    out = {}
    for key, name, unit, dev_class in sensors:
        topic = "%s/sensor/%s/%s/config" % (base_topic, node_id, key)
        payload = {
            "name": "%s %s" % (node_id, name),
            "state_topic": state_topic,
            "unique_id": "%s_%s" % (node_id, key),
            "value_template": "{{ value_json.%s }}" % key,
            "device": device,
        }
        if unit:
            payload["unit_of_measurement"] = unit
        if dev_class:
            payload["device_class"] = dev_class
        out[topic] = payload
    return out


class HAMqtt(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Publish Pwnagotchi sensors to Home Assistant via MQTT discovery."

    def __init__(self):
        self.options = dict()
        self._client = None
        self._connected = False
        self._handshakes = 0
        self._last_pub = 0

    def on_loaded(self):
        self._host = self.options.get("host", "127.0.0.1")
        self._port = int(self.options.get("port", 1883))
        self._user = self.options.get("username")
        self._pass = self.options.get("password")
        self._base = self.options.get("base_topic", "homeassistant")
        self._node = self.options.get("node_id") or socket.gethostname()
        self._interval = float(self.options.get("interval", 30))
        logging.info("[ha_mqtt] loaded (node=%s broker=%s:%d)", self._node, self._host, self._port)

    # -- value gathering (testable) ----------------------------------------------------
    def gather_values(self):
        vals = {"handshakes": self._handshakes}
        try:
            vals["temperature"] = round(float(pwnagotchi.temperature()), 1)
        except Exception:
            pass
        try:
            vals["cpu"] = round(float(pwnagotchi.cpu_load()) * 100, 1)
        except Exception:
            pass
        try:
            vals["memory"] = round(float(pwnagotchi.mem_usage()) * 100, 1)
        except Exception:
            pass
        try:
            vals["uptime"] = int(pwnagotchi.uptime())
        except Exception:
            pass
        return vals

    def build_state_payload(self):
        return self.gather_values()

    # -- mqtt (guarded, not unit-tested) -----------------------------------------------
    def _setup(self):
        try:
            import paho.mqtt.client as mqtt
        except Exception as e:
            logging.warning("[ha_mqtt] paho-mqtt not installed; idling: %s", e)
            return
        try:
            self._client = mqtt.Client()
            if self._user:
                self._client.username_pw_set(self._user, self._pass)
            self._client.connect(self._host, self._port, keepalive=60)
            self._client.loop_start()
            self._connected = True
            self._publish_discovery()
        except Exception as e:
            logging.warning("[ha_mqtt] connect failed; idling: %s", e)
            self._connected = False

    def _publish_discovery(self):
        if not self._client:
            return
        for topic, payload in build_discovery_configs(self._node, self._base).items():
            try:
                self._client.publish(topic, json.dumps(payload), retain=True)
            except Exception as e:
                logging.debug("[ha_mqtt] discovery publish failed: %s", e)

    def _publish_state(self):
        if not (self._client and self._connected):
            return
        try:
            self._client.publish(state_topic_for(self._base, self._node),
                                 json.dumps(self.build_state_payload()))
        except Exception as e:
            logging.debug("[ha_mqtt] state publish failed: %s", e)

    # -- events ------------------------------------------------------------------------
    def on_ready(self, agent):
        self._setup()

    def on_handshake(self, agent, filename, access_point, client_station):
        self._handshakes += 1

    def on_epoch(self, agent, epoch, epoch_data):
        now = time.time()
        if (now - self._last_pub) >= self._interval:
            self._last_pub = now
            self._publish_state()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("hamqtt", LabeledValue(color=BLACK, label="mqtt:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("hamqtt", "on" if self._connected else "off")

    def on_unload(self, ui):
        try:
            if self._client:
                self._client.loop_stop()
                self._client.disconnect()
        except Exception:
            pass
        with ui._lock:
            if ui.has_element("hamqtt"):
                ui.remove_element("hamqtt")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        vals = self.gather_values()
        rows = "".join("<tr><td>{}</td><td>{}</td></tr>".format(k, v) for k, v in vals.items())
        return ("<html><body><h1>HA MQTT</h1><p>connected: {}</p>"
                "<table border=1>{}</table></body></html>").format(self._connected, rows)
