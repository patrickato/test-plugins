"""env_sensors — log real ambient conditions from I2C sensors.

`memtemp` reads the SoC only; nothing logs the surrounding environment. This polls one or more
attached I2C sensors — temperature, humidity, pressure, light — behind a single driver
interface, so several chip types can be mixed and configured together. Shows a primary reading
on the display and all readings on the web page.

Supported driver types: `bme280` (temp/pressure/humidity), `sht3x` (temp/humidity),
`tsl2591` (lux), and `mock` (for testing). Each driver lazily imports its library and is
skipped cleanly if the library or bus isn't present.

Options (main.plugins.env_sensors.*):
    enabled  = true
    sensors  = [ { type = "bme280", address = "0x76", name = "weather" } ]
    position = "0,0"

Requires: I²C enabled + pip `smbus2` (bme280/sht3x) and/or the relevant Adafruit lib
(tsl2591); a supported I²C sensor. With no library/sensor the plugin simply reports nothing.
"""
import logging

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def parse_address(value, default):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    s = str(value).strip()
    try:
        return int(s, 16) if s.lower().startswith("0x") else int(s)
    except ValueError:
        return default


class MockDriver:
    def __init__(self, address, opts):
        self.available = True
        self._values = dict(opts.get("values", {}))

    def read(self):
        return dict(self._values)


class BME280Driver:
    def __init__(self, address, opts):
        self.address = parse_address(address, 0x76)
        self.bus_no = int(opts.get("bus", 1))
        self.available = False
        self._cal = None
        try:
            import smbus2
            import bme280
            self._smbus2, self._bme280 = smbus2, bme280
            self.available = True
        except Exception:
            pass

    def read(self):
        if not self.available:
            return {}
        try:
            bus = self._smbus2.SMBus(self.bus_no)
            if self._cal is None:
                self._cal = self._bme280.load_calibration_params(bus, self.address)
            d = self._bme280.sample(bus, self.address, self._cal)
            return {"temperature_C": round(d.temperature, 2),
                    "pressure_hPa": round(d.pressure, 2),
                    "humidity": round(d.humidity, 2)}
        except Exception:
            return {}


class SHT3xDriver:
    def __init__(self, address, opts):
        self.address = parse_address(address, 0x44)
        self.bus_no = int(opts.get("bus", 1))
        self.available = False
        try:
            import smbus2
            self._smbus2 = smbus2
            self.available = True
        except Exception:
            pass

    def read(self):
        if not self.available:
            return {}
        try:
            import time
            bus = self._smbus2.SMBus(self.bus_no)
            bus.write_i2c_block_data(self.address, 0x2C, [0x06])
            time.sleep(0.05)
            raw = bus.read_i2c_block_data(self.address, 0x00, 6)
            t_raw = raw[0] << 8 | raw[1]
            h_raw = raw[3] << 8 | raw[4]
            return {"temperature_C": round(-45 + 175 * t_raw / 65535.0, 2),
                    "humidity": round(100 * h_raw / 65535.0, 2)}
        except Exception:
            return {}


class TSL2591Driver:
    def __init__(self, address, opts):
        self.available = False
        try:
            import board
            import adafruit_tsl2591
            self._sensor = adafruit_tsl2591.TSL2591(board.I2C())
            self.available = True
        except Exception:
            pass

    def read(self):
        if not self.available:
            return {}
        try:
            return {"lux": round(float(self._sensor.lux), 1)}
        except Exception:
            return {}


DRIVERS = {"mock": MockDriver, "bme280": BME280Driver, "sht3x": SHT3xDriver, "tsl2591": TSL2591Driver}


class EnvSensors(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Log ambient temp/humidity/pressure/light from one or more I2C sensors."

    def __init__(self):
        self.options = dict()
        self._sensors = []       # list of (name, driver)
        self._latest = {}        # name -> readings dict

    def on_loaded(self):
        self._sensors = self._build_sensors(self.options.get("sensors", []))
        logging.info("[env_sensors] loaded (%d active sensor(s))", len(self._sensors))

    def _build_sensors(self, specs):
        built = []
        for spec in specs or []:
            if not isinstance(spec, dict):
                continue
            stype = spec.get("type")
            factory = DRIVERS.get(stype)
            if factory is None:
                logging.warning("[env_sensors] unknown sensor type '%s'; skipping", stype)
                continue
            try:
                drv = factory(spec.get("address"), spec)
            except Exception as e:
                logging.warning("[env_sensors] %s init failed: %s", stype, e)
                continue
            if not getattr(drv, "available", False):
                logging.warning("[env_sensors] %s not available (missing lib/bus); skipping", stype)
                continue
            name = spec.get("name") or stype
            built.append((name, drv))
        return built

    # -- core --------------------------------------------------------------------------
    def poll(self):
        for name, drv in self._sensors:
            try:
                readings = drv.read()
            except Exception:
                readings = {}
            if readings:
                self._latest[name] = readings
        return self._latest

    def _ui_value(self):
        for readings in self._latest.values():
            if "temperature_C" in readings:
                return "%.0fC" % readings["temperature_C"]
            if "lux" in readings:
                return "%.0flx" % readings["lux"]
            if "humidity" in readings:
                return "%.0f%%" % readings["humidity"]
        return "-"

    # -- events ------------------------------------------------------------------------
    def on_epoch(self, agent, epoch, epoch_data):
        if self._sensors:
            self.poll()

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("env", LabeledValue(color=BLACK, label="env:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("env", self._ui_value())

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("env"):
                ui.remove_element("env")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        self.poll()
        rows = "".join(
            "<tr><td>{}</td><td>{}</td></tr>".format(name, readings)
            for name, readings in self._latest.items()
        ) or "<tr><td colspan=2>no sensors / no readings</td></tr>"
        return ("<html><body><h1>Environmental Sensors</h1>"
                "<table border=1><tr><th>sensor</th><th>readings</th></tr>{}"
                "</table></body></html>").format(rows)
