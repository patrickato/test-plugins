"""Off-Pi test harness for Pwnagotchi plugins.

Real Pwnagotchi can't be imported off-device (it needs prctl, hardware, a running
agent). So before any plugin module is imported, we register a lightweight *fake*
``pwnagotchi`` package tree in ``sys.modules``. Plugins then import the fakes and can be
exercised in plain pytest with no hardware.

The fakes are deliberately minimal: a plain ``Plugin`` base (no threading/prctl), UI
widget stand-ins that record their construction args, and a ``FakeUI``/``FakeAgent`` that
record calls so tests can assert behaviour.
"""
import importlib.util
import sys
import threading
import types
from pathlib import Path

import pytest

PLUGINS_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------------------
# Fake `pwnagotchi` package tree, registered once at import time.
# --------------------------------------------------------------------------------------
def _install_fake_pwnagotchi():
    if "pwnagotchi" in sys.modules and getattr(sys.modules["pwnagotchi"], "_is_fake", False):
        return

    # pwnagotchi
    pwn = types.ModuleType("pwnagotchi")
    pwn._is_fake = True
    pwn.config = {"main": {"plugins": {}}}
    pwn.mem_usage = lambda: 0.42
    pwn.cpu_load = lambda: 0.17
    pwn.temperature = lambda celsius=True: 48 if celsius else 118
    pwn.uptime = lambda: 12345

    # pwnagotchi.plugins  (plain base — no auto-register machinery)
    plugins = types.ModuleType("pwnagotchi.plugins")

    class Plugin:
        options = {}

    plugins.Plugin = Plugin
    plugins.loaded = {}
    pwn.plugins = plugins

    # pwnagotchi.ui + submodules
    ui = types.ModuleType("pwnagotchi.ui")

    components = types.ModuleType("pwnagotchi.ui.components")

    class _Widget:
        """Records constructor args so tests can inspect what a plugin built."""
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def draw(self, *a, **k):  # never actually rendered in tests
            pass

    for _name in ("Widget", "Bitmap", "Line", "Rect", "FilledRect", "Text", "LabeledValue"):
        setattr(components, _name, type(_name, (_Widget,), {}))

    view = types.ModuleType("pwnagotchi.ui.view")
    view.BLACK = 0
    view.WHITE = 0xFF
    view.ROOT = None

    fonts = types.ModuleType("pwnagotchi.ui.fonts")
    for _f in ("Small", "Medium", "MediumSmall", "Bold", "BoldSmall", "BoldBig", "Huge"):
        setattr(fonts, _f, None)

    ui.components = components
    ui.view = view
    ui.fonts = fonts
    pwn.ui = ui

    for name, mod in {
        "pwnagotchi": pwn,
        "pwnagotchi.plugins": plugins,
        "pwnagotchi.ui": ui,
        "pwnagotchi.ui.components": components,
        "pwnagotchi.ui.view": view,
        "pwnagotchi.ui.fonts": fonts,
    }.items():
        sys.modules[name] = mod


_install_fake_pwnagotchi()


# --------------------------------------------------------------------------------------
# Test doubles for the objects plugins receive at runtime.
# --------------------------------------------------------------------------------------
class FakeUI:
    """Stands in for the Pwnagotchi View passed to on_ui_setup/update/unload."""
    def __init__(self):
        self.elements = {}
        self.values = {}
        self._lock = threading.RLock()

    # element management -----------------------------------------------------
    def add_element(self, key, elem):
        self.elements[key] = elem
        self.values.setdefault(key, getattr(elem, "kwargs", {}).get("value", ""))

    def remove_element(self, key):
        self.elements.pop(key, None)
        self.values.pop(key, None)

    def has_element(self, key):
        return key in self.elements

    def set(self, key, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    # display-type predicates — default everything to False so plugins take
    # their generic/default layout branch in tests.
    def __getattr__(self, name):
        if name.startswith("is_"):
            return lambda: False
        raise AttributeError(name)


class FakeAgent:
    """Minimal agent stand-in for on_ready/on_handshake/on_epoch/etc."""
    def __init__(self, config=None):
        self._config = config or {"main": {"plugins": {}}}

    def config(self):
        return self._config


@pytest.fixture
def ui():
    return FakeUI()


@pytest.fixture
def agent():
    return FakeAgent()


@pytest.fixture
def load_plugin():
    """Import a plugin .py by path and return an instance of its Plugin subclass.

    Usage:  plugin = load_plugin('templates/plugin_template.py', options={...})
    Paths are resolved relative to the pwnagotchi-plugins/ root.
    """
    from pwnagotchi.plugins import Plugin

    def _load(rel_path, options=None):
        path = (PLUGINS_ROOT / rel_path).resolve()
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = next(
            obj for obj in vars(module).values()
            if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin
        )
        instance = cls()
        if not hasattr(instance, "options") or instance.options is None:
            instance.options = {}
        if options:
            instance.options.update(options)
        return instance

    return _load
