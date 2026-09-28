import logging
import threading
from datetime import datetime, timedelta

import pwnagotchi.plugins as plugins


class TargetedKick(plugins.Plugin):
    """
    TargetedKick - pwnagotchi plugin

    Deauths one specific connected client at a time per AP, instead of
    however many clients pwnagotchi's default behavior might otherwise
    disconnect at once. Useful for testing your own network's
    reconnection behavior client-by-client rather than knocking your
    whole household offline in one shot.

    REQUIRES the same config change as PMKIDFirst: turn off
    pwnagotchi's own built-in deauth so this plugin controls it:

        personality.associate = true
        personality.deauth = false

    With core deauth off, this plugin becomes the only source of deauth
    activity, and it always targets exactly one client per AP per
    attempt, cycling to the next client only after a cooldown period
    (so it isn't just deauthing the same one client on a tight loop
    either).
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Deauths exactly one connected client per AP at a time, '
        'cycling through clients with a cooldown, instead of '
        'disconnecting every client on an AP at once. Requires '
        'personality.deauth = false.'
    )

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.ap_state = {}  # bssid -> {"ssid", "client_index", "last_kick", "clients_tried"}

    def on_loaded(self):
        cfg = self.options
        self.cooldown_secs = int(cfg.get('per_client_cooldown_secs', 60))
        self.ready = True
        logging.info(
            "[TargetedKick] plugin loaded, per_client_cooldown_secs=%d. "
            "Reminder: set personality.deauth = false for this plugin to "
            "control deauth itself.",
            self.cooldown_secs
        )

    def on_wifi_update(self, agent, access_points):
        if not self.ready:
            return

        now = datetime.now()

        for ap in access_points:
            bssid = (ap.get('mac') or '').lower()
            ssid = ap.get('hostname') or ap.get('ssid') or '(hidden)'
            clients = ap.get('clients') or []
            if not bssid or not clients:
                continue

            with self.lock:
                state = self.ap_state.setdefault(bssid, {
                    "ssid": ssid, "client_index": 0, "last_kick": None, "clients_tried": set()
                })

                if state["last_kick"] and (now - state["last_kick"]).total_seconds() < self.cooldown_secs:
                    continue  # still cooling down from the last kick on this AP

                # pick next client in rotation
                idx = state["client_index"] % len(clients)
                target = clients[idx]
                target_mac = target.get('mac', '?')

                try:
                    agent.deauth(ap, target)
                    state["last_kick"] = now
                    state["client_index"] += 1
                    state["clients_tried"].add(target_mac)
                    logging.info(
                        "[TargetedKick] '%s' (%s): deauthed client %s only "
                        "(%d/%d clients on this AP tried so far)",
                        ssid, bssid, target_mac, len(state["clients_tried"]), len(clients)
                    )
                except Exception as e:
                    logging.error(
                        "[TargetedKick] deauth failed for '%s' client %s: %s - "
                        "check agent.deauth() signature for your version",
                        ssid, target_mac, e
                    )
