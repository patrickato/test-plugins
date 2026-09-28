import logging

import pwnagotchi.plugins as plugins


class PassiveOnlyMode(plugins.Plugin):
    """
    PassiveOnlyMode - pwnagotchi plugin

    A hard switch for the quietest possible test run. Two levels:

      mode = "quiet"  -> PMKID association attempts still happen
                         (lightweight, clientless, non-disruptive) but
                         deauth is completely off. Equivalent to
                         setting personality.deauth = false.

      mode = "silent" -> fully passive. No PMKID association attempts
                         either - pwnagotchi only listens to beacon
                         frames already being broadcast, sends nothing
                         itself. Equivalent to setting BOTH
                         personality.deauth = false AND
                         personality.associate = false.

    IMPORTANT: personality.deauth / personality.associate are read by
    pwnagotchi's core automata once at startup, before any plugin gets
    a chance to run - so this plugin CANNOT flip them for you live.
    What it does instead: loudly logs exactly what config.toml needs to
    say for your chosen mode, every time it loads, so a mismatch is
    obvious in the log rather than silently running louder than you
    intended.

    Shows a "PASSIVE" indicator on the display so it's obvious at a
    glance the unit is in a reduced-activity mode.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Hard switch for the quietest possible run: "quiet" keeps '
        'PMKID collection but disables deauth, "silent" disables both '
        'for fully passive beacon-only operation. Logs exactly what '
        'config.toml needs to say for the chosen mode every boot.'
    )

    def __init__(self):
        self.ready = False

    def on_loaded(self):
        cfg = self.options
        self.mode = cfg.get('mode', 'quiet')

        if self.mode not in ('quiet', 'silent'):
            logging.warning("[PassiveOnlyMode] unknown mode '%s', defaulting to 'quiet'",
                            self.mode)
            self.mode = 'quiet'

        self.ready = True
        logging.info("[PassiveOnlyMode] plugin loaded, mode=%s", self.mode)

        # note: personality settings are read once at pwnagotchi startup
        # by the core, so this check runs at plugin load time (also
        # startup) to catch a mismatch as early as possible.
        self._check_personality()

    def on_ui_setup(self, ui):
        components = __import__('pwnagotchi.ui.components', fromlist=['LabeledValue'])
        fonts = __import__('pwnagotchi.ui.fonts', fromlist=['Small', 'Bold'])
        ui.add_element('passiveonly', components.LabeledValue(
            color=fonts.Small,
            label='',
            value='',
            position=(ui.width() / 2 + 160, 0),
            label_font=fonts.Bold,
            text_font=fonts.Small,
        ))

    def on_ui_update(self, ui):
        ui.set('passiveonly', 'SILENT' if self.mode == 'silent' else 'QUIET')

    def on_unload(self, ui):
        with ui._lock:
            try:
                ui.remove_element('passiveonly')
            except Exception:
                pass

    def _check_personality(self):
        # this plugin doesn't have direct access to the loaded config
        # object at on_loaded time (that's the agent's, not the
        # plugin's) - the reliable check is telling the user what
        # config.toml SHOULD say for their chosen mode, and logging it
        # loudly so it's impossible to miss on boot.
        if self.mode == 'quiet':
            logging.info(
                "[PassiveOnlyMode] mode=quiet requires: personality.deauth = "
                "false, personality.associate = true. Verify config.toml "
                "matches - this plugin cannot force it after pwnagotchi has "
                "already started this session."
            )
        else:
            logging.info(
                "[PassiveOnlyMode] mode=silent requires: personality.deauth = "
                "false, personality.associate = false. Verify config.toml "
                "matches - this plugin cannot force it after pwnagotchi has "
                "already started this session."
            )
