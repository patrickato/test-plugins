import logging
import threading
from datetime import datetime

import pwnagotchi.plugins as plugins


class AdaptiveDeauth(plugins.Plugin):
    """
    AdaptiveDeauth - pwnagotchi plugin

    Tracks how many deauth attempts have been made against each AP and
    how many of those actually produced a handshake, then scales back
    how often a non-responsive AP gets deauthed again - instead of
    pwnagotchi's default of hitting every AP the same way every epoch
    regardless of whether it's working.

    Behavior:
      - First `initial_attempts` deauths against an AP happen at normal
        pace (this plugin doesn't interfere).
      - If none of those produced a handshake, the AP enters a
        "backing off" state: further deauth attempts against it are
        skipped for an increasing cooldown window (doubles each time,
        up to `max_backoff_secs`).
      - The moment a handshake IS produced for an AP, its backoff state
        is cleared - a working AP is never throttled.

    This is a pace-limiter on pwnagotchi's existing default deauth
    behavior (which already targets any non-whitelisted AP it
    encounters) - it doesn't add new targets, it just stops repeatedly
    hammering ones that clearly aren't responding.

    NOTE: this plugin can't intercept pwnagotchi's own deauth calls
    directly (the core automata decides when to call agent.deauth()
    itself). Instead it works by temporarily adding an AP that's in
    backoff to pwnagotchi's whitelist for the duration of the cooldown
    window, then removing it again once the cooldown expires - using
    the same live+persisted whitelist mechanism as HandshakeCompleter.
    This is a workaround, not a direct hook into the attack decision,
    so check the log to confirm it's behaving as expected on your
    version.
    """

    __author__ = 'patrickato'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = (
        'Backs off deauth attempts against APs that repeatedly fail to '
        'produce a handshake, using temporary whitelist entries with an '
        'increasing cooldown, instead of hammering the same '
        'non-responsive AP every epoch indefinitely.'
    )

    CONFIG_PATH = '/etc/pwnagotchi/config.toml'

    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.ap_stats = {}  # bssid -> {"ssid", "attempts", "backoff_until", "backoff_secs"}

    def on_loaded(self):
        cfg = self.options
        self.initial_attempts = int(cfg.get('initial_attempts', 3))
        self.base_backoff_secs = int(cfg.get('base_backoff_secs', 300))
        self.max_backoff_secs = int(cfg.get('max_backoff_secs', 3600))
        self.ready = True
        logging.info(
            "[AdaptiveDeauth] plugin loaded, initial_attempts=%d, "
            "base_backoff_secs=%d, max_backoff_secs=%d",
            self.initial_attempts, self.base_backoff_secs, self.max_backoff_secs
        )

    def on_deauthentication(self, agent, access_point, client_station):
        # fires whenever pwnagotchi (or this plugin's earlier state)
        # sends a deauth - count the attempt
        bssid = (access_point or {}).get('mac', '').lower()
        ssid = (access_point or {}).get('hostname', '') or '(hidden)'
        if not bssid:
            return

        with self.lock:
            stats = self.ap_stats.setdefault(bssid, {
                "ssid": ssid, "attempts": 0, "backoff_until": None, "backoff_secs": self.base_backoff_secs
            })
            stats["attempts"] += 1

            if stats["attempts"] >= self.initial_attempts and not stats["backoff_until"]:
                self._start_backoff(agent, bssid, ssid, stats)

    def on_handshake(self, agent, filename, access_point, client_station):
        bssid = (access_point or {}).get('mac', '').lower()
        with self.lock:
            if bssid in self.ap_stats:
                logging.info(
                    "[AdaptiveDeauth] '%s' produced a handshake - clearing "
                    "backoff state, it's working", self.ap_stats[bssid]["ssid"]
                )
                self._end_backoff(agent, bssid)
                del self.ap_stats[bssid]

    def on_wifi_update(self, agent, access_points):
        # check for backoff windows that have expired and remove them
        now = datetime.now()
        with self.lock:
            for bssid, stats in list(self.ap_stats.items()):
                if stats["backoff_until"] and now >= stats["backoff_until"]:
                    logging.info(
                        "[AdaptiveDeauth] '%s' backoff window expired, "
                        "removing temporary whitelist hold", stats["ssid"]
                    )
                    self._end_backoff(agent, bssid)
                    stats["backoff_until"] = None
                    stats["attempts"] = 0
                    # next backoff, if needed again, doubles from here
                    stats["backoff_secs"] = min(stats["backoff_secs"] * 2, self.max_backoff_secs)

    # ---------------------------------------------------------------

    def _start_backoff(self, agent, bssid, ssid, stats):
        from datetime import timedelta
        stats["backoff_until"] = datetime.now() + timedelta(seconds=stats["backoff_secs"])
        self._whitelist_add(agent, ssid)
        logging.info(
            "[AdaptiveDeauth] '%s' (%s): %d deauth attempts, no handshake - "
            "backing off for %ds (temporary whitelist hold)",
            ssid, bssid, stats["attempts"], stats["backoff_secs"]
        )

    def _end_backoff(self, agent, bssid):
        stats = self.ap_stats.get(bssid)
        if stats:
            self._whitelist_remove(agent, stats["ssid"])

    def _whitelist_add(self, agent, ssid):
        try:
            cfg = getattr(agent, '_config', None) or getattr(agent, 'config', None)
            if cfg and 'main' in cfg and 'whitelist' in cfg['main']:
                if ssid not in cfg['main']['whitelist']:
                    cfg['main']['whitelist'].append(ssid)
        except Exception as e:
            logging.debug("[AdaptiveDeauth] live whitelist add failed: %s", e)
        # intentionally NOT persisted to config.toml - this is a temporary,
        # in-memory-only hold, not a permanent whitelist change

    def _whitelist_remove(self, agent, ssid):
        try:
            cfg = getattr(agent, '_config', None) or getattr(agent, 'config', None)
            if cfg and 'main' in cfg and 'whitelist' in cfg['main']:
                if ssid in cfg['main']['whitelist']:
                    cfg['main']['whitelist'].remove(ssid)
        except Exception as e:
            logging.debug("[AdaptiveDeauth] live whitelist remove failed: %s", e)
