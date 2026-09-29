# Notes: Novelty / Games / Personality cluster

**Status: IN PROGRESS. Findings for the full 13-entry cluster
presented; 5 removed at the user's request so far
(`bitcoin.py`, `christmas.py`, `envtune`, `miyagi.py`, `partymode.py`).
The remaining 8 (`achievements.py`, `birthday.py`, `counter.py`,
`fortune_cookie.py`, `IPDisplay.py`, `spam_peers.py`, `Weather.py`,
`wifi_adventures.py`) are still awaiting a decision - nothing has been
fixed/rebuilt/moved to `plugins-wip` yet.** 6 bullets were duplicate
listings already reviewed in Clusters 16/17 (`age.py`, `agev2.py`,
`age.py` AlienMajik variant, `expv2.py`, `xp.py`, `xp_grid.py`) - no
new action taken on them here.

All source read from `itsdarklikehell/pwnagotchi-plugins/` unless
otherwise noted (`spam_peers.py` from
`sniffleupagus/pwnagotchi_plugins/`), checked against the real cloned
`jayofelony/pwnagotchi` framework.

## Removed at the user's request (5)

- **`bitcoin.py`** - `on_sleep(self)` has the wrong signature; the
  real hook is `on_sleep(self, agent, t)`. Since `on_sleep` is the
  only caller of `_fetch_price()`, this is a guaranteed `TypeError`
  every single sleep cycle - the plugin's entire feature never worked,
  ever. Also had dead unused `api_url`/`bitcoin_api_url` config keys,
  and a possibly-defunct API endpoint (the coindesk BPI API was
  discontinued in 2022, per general knowledge - not independently
  re-verified this pass). **Correction to an earlier internal note**:
  `on_ui_setup`'s `ui.is_waveshare_v2()`-style calls were initially
  suspected of also being broken based on an earlier Cluster 34
  finding about `crack_house.py` - this was empirically disproved
  (see the Cluster 34 correction note, added separately); it was
  never the reason this plugin didn't work.
- **`christmas.py`** - reviewed with no fatal bugs found (well-wrapped
  in try/except throughout; its one minor issue is `__dependencies__`
  wrongly declaring the stdlib `datetime` as a pip package). Dropped
  anyway at the user's request rather than kept as-is.
- **`envtune`** - no source code locatable anywhere across every
  archive searched for this project. Removed, record only, same
  pattern as `PwnSpotify`/`Showerthoughts` in Cluster 35.
- **`miyagi.py`** - built entirely around a self-play `[ai]` model
  training subsystem that does not exist on this fork at all -
  confirmed via a full grep of `pwnagotchi/defaults.toml` (no `[ai]`
  section anywhere) and of every `plugins.on(...)` call site in the
  framework (none of `on_ai_ready`, `on_ai_policy`,
  `on_ai_training_start/step/end`, `on_ai_best_reward`, or
  `on_ai_worst_reward` are ever fired). Roughly half the plugin's
  hooks are consequently permanent dead code. Worse, `on_ready`
  unconditionally does `self.agent._config["ai"]["path"]` with no
  guard at all - a guaranteed `KeyError` aborting `on_ready` on every
  single daemon startup, before the plugin does anything useful.
- **`partymode.py`** - `on_loaded` monkeypatches the shared, global
  `pwnagotchi.ui.view.BLACK`/`WHITE` module-level constants to random
  hex **strings** (e.g. `"0X4A"`) instead of ints. These constants
  feed PIL drawing calls across the *entire* UI stack, not just this
  plugin's own elements, so the type mismatch risks breaking
  rendering globally, not just cosmetically for this one plugin. It
  also removes and re-adds every single UI element on every single
  `on_ui_update` tick (once per render), churning shared global state
  far more aggressively than its cosmetic goal warrants.

## Findings presented, decision still pending (8)

- **`achievements.py`** - `on_unfiltered_ap_list(self, agent)` has the
  wrong signature; the real hook is `on_unfiltered_ap_list(self,
  agent, access_points)` - a guaranteed `TypeError` every time it
  fires, permanently soft-locking the "new network"
  achievement-challenge type. Also a dead, unreachable duplicate
  `choose_random_challenge()` instance method (harmless, the real
  module-level function is the only one ever called). Suggested
  action: fix and rebuild.
- **`birthday.py`** - three real bugs: (1) `__defaults__` only sets
  `enabled: False`, but `self.options["show_age"]`/`["show_birthday"]`/
  `["age_x_coord"]`/`["age_y_coord"]` are all directly indexed with no
  fallback - `KeyError` on load if any is unset; (2) imports
  `dateutil.relativedelta` but `__dependencies__` declares `"pip":
  ["none"]` - wrong dependency declaration; (3) `load_data()` does
  `data["born_at"]` via direct indexing on `/root/brain.json` - a
  missing key would silently leave the age at a bogus Unix-epoch
  default instead of failing visibly. Suggested action: fix and
  rebuild.
- **`counter.py`** - no framework-misuse bugs found. Declares an
  unused `scapy` pip dependency - a cosmetic nit. Suggested action:
  keep as-is or trivial fix, low priority.
- **`fortune_cookie.py`** - no `__defaults__` dict anywhere in the
  class at all, yet `self.options['orientation']`/`['enabled']` are
  both directly indexed with no fallback - `KeyError` on load/update
  for a brand-new install. The `orientation` option is also a no-op -
  both its "vertical"/"horizontal" branches build byte-for-byte
  identical UI elements. Suggested action: fix and rebuild.
- **`IPDisplay.py`** - solid, defensively-coded plugin overall (uses
  `'key' in self.options` checks throughout). One minor, low-severity
  issue: a possible `IndexError` if the interface list is ever empty,
  already caught by the surrounding `try/except`. Suggested action:
  keep as-is, or trivial fix.
- **`spam_peers.py`** - `__init__` does raw, unguarded
  `os.listdir("/root/peers")` with no existence check. Since
  `Plugin.__init_subclass__` calls `cls()` immediately with no
  try/except anywhere in the loader, a `FileNotFoundError` here (e.g.
  a fresh install with no peers dir yet) crashes the plugin's
  *loading* entirely, not just one hook. Also `on_peer_detected` does
  `peer.adv['identity']` via raw dict indexing - the real `Peer` class
  explicitly guards against a malformed/null advertisement (`self.adv
  = {}`) with its own defensive `_adv_str()` accessor; direct
  indexing here crashes on exactly the case the framework itself
  guards against. Suggested action: fix and rebuild.
- **`Weather.py`** - hardcoded OpenWeatherMap API key and hardcoded
  location ("Leeuwarden") baked into the source with zero config
  options - unusable/insecure for anyone but the original author, and
  the embedded key is exposed to anyone reading the file. Also wrongly
  declares `"pip": ["scapy"]` instead of what it actually needs.
  Suggested action: fix and rebuild (add config options), or remove.
- **`wifi_adventures.py`** - of 6 "adventure type" hook methods, only
  2 (`on_handshake`, `on_unfiltered_ap_list`) are real pwnagotchi
  framework hooks - the other 4 (`on_packet_party`, `on_pixel_parade`,
  `on_data_dazzle`, `on_speedy_scan`) are not real hook names this
  framework ever calls, and are permanently dead code along with
  everything they alone call (a blocking-`input()` treasure-hunt
  minigame, an unused wifi-auto-connect-via-cracked-password routine).
  Of the 2 real hooks: `on_unfiltered_ap_list` has the wrong signature
  (missing `access_points`); `on_handshake` calls a helper with one
  argument against a 2-argument signature - both guaranteed
  `TypeError`s. Also POSTs telemetry to a hardcoded personal IP.
  Suggested action: remove, or full rewrite keeping only the
  achievement concept built around the two real hooks.

## A correction surfaced during this review (written into Cluster 34's docs)

While researching `bitcoin.py`'s `on_ui_setup` (which calls
`ui.is_waveshare_v2()`-style methods, the same pattern flagged as
broken in an earlier Cluster 34 finding about `crack_house.py`), this
was checked empirically rather than taken on faith: a real `Display`
object was constructed in the sandbox from the real
`pwnagotchi/defaults.toml`, and `plugins.on` was instrumented to
capture exactly what `on_ui_setup` receives. Result: `on_ui_setup`'s
`ui` parameter genuinely is a `Display` instance (not a bare `View`),
so these calls don't crash. The same reasoning applies to
`on_ui_update` and `ui.init_display()`, which affects the
`screen_refresh.py` writeup too. A correction section has been added
to `cluster-34-display-ui/NOTES.md` documenting this - it doesn't
change either affected plugin's already-decided disposition, just
corrects the record. See that file for full detail.

## Still open

- Decisions pending on the 8 plugins listed above.
- `spotify_now_playing.py` (Cluster 35) remains deferred, not
  addressed this pass.
