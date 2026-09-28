# Interesting Shortlist - Saved for Later

Plugins flagged as worth a second look during the elimination process, not
tied to any removal criterion - just genuinely useful/clever finds. Not
committed to being kept or built yet, just parked here so they don't get
lost in the noise of the bigger list.

1. **`apprise-notify.py`** - One plugin, dozens of possible notification destinations via the Apprise library. Could cover Discord/Slack/Telegram/ntfy/etc. through one config instead of five separate plugins.
2. **`ext_wifi.py` / `extWifi.py`** - Directly answers the external-adapter question from earlier in this project (frees the onboard WiFi chip for an external one). Worth testing once you get an adapter.
3. **`potfilesorter.py`** - Turns a hashcat potfile straight into a ready-to-use `wpa_supplicant.conf`. Nobody else on the list does that conversion.
4. **`RaspiSyncedTime.py`** - Clever fix for timestamp accuracy with no RTC and no GPS time source.
5. **`wd_honey_Pot.py`** - The one genuinely defensive plugin on the whole list: detects *other* pwnagotchis deauthing near you, rather than attacking anything itself. Given your rural setup, probably low real-world hit rate, but a neat concept.
6. **`state-api.py`** - Small JSON API that other fancier tools (pwmenu-style consoles, dashboards) build on top of. Worth keeping in mind as infrastructure even if not used directly.
7. **`skyhigh.py`** - Aircraft tracking via the OpenSky API with zero extra hardware needed.
8. **`handshaker.py`** - Pull key pwnagotchi info over an alternate channel when SSH is down.
9. **`mqtt_plugin.py`** - If home automation ever enters the tinker shop, this is the bridge that lets pwnagotchi talk to that world.

---
*Compiled by Claude · 2026-09-28*
