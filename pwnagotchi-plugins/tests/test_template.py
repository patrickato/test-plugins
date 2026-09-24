"""Sanity test proving the harness works: load the template plugin and drive its hooks."""


def test_template_lifecycle(load_plugin, ui, agent):
    plugin = load_plugin("templates/plugin_template.py", options={"label": "DEMO", "position": "10,20"})

    # loaded -> ready
    plugin.on_loaded()
    plugin.on_ready(agent)

    # UI setup adds a namespaced element with the configured label + position
    plugin.on_ui_setup(ui)
    assert ui.has_element("tmpl_val")
    elem = ui.elements["tmpl_val"]
    assert elem.kwargs["label"] == "DEMO:"
    assert elem.kwargs["position"] == (10, 20)

    # UI update reflects readiness
    plugin.on_ui_update(ui)
    assert ui.get("tmpl_val") == "ok"

    # unload cleans up
    plugin.on_unload(ui)
    assert not ui.has_element("tmpl_val")


def test_template_webhook(load_plugin):
    plugin = load_plugin("templates/plugin_template.py")
    plugin.on_loaded()
    body = plugin.on_webhook("/", request=None)
    assert "plugin_template" in body


def test_template_survives_missing_options(load_plugin, ui, agent):
    # No options at all -> must not crash; falls back to defaults.
    plugin = load_plugin("templates/plugin_template.py")
    plugin.on_loaded()
    plugin.on_ready(agent)
    plugin.on_ui_setup(ui)
    plugin.on_ui_update(ui)
    plugin.on_unload(ui)
    assert not ui.has_element("tmpl_val")
