# Notes: Novelty / Games / Personality cluster

**Status: DONE (except `achievements.py`, explicitly deferred).** 5
removed at the user's request (`bitcoin.py`, `christmas.py`,
`envtune`, `miyagi.py`, `partymode.py`). `achievements.py`'s decision
was explicitly deferred - findings presented, but left on the list
for a later pass rather than fixed now. `counter.py` and `IPDisplay.py`
reviewed with no fatal bugs and kept as-is. 5 fixed/rebuilt and moved
to `plugins-wip`, each with user-approved upgrades:
`birthday.py` -> `BirthdayNG`, `fortune_cookie.py` -> `FortuneCookieNG`,
`spam_peers.py` -> `SpamPeersNG`, `Weather.py` -> `WeatherNG`,
`wifi_adventures.py` -> `WifiAdventuresNG`. 6 bullets were duplicate
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

## Deferred at the user's explicit request (1)

- **`achievements.py`** - `on_unfiltered_ap_list(self, agent)` has the
  wrong signature; the real hook is `on_unfiltered_ap_list(self,
  agent, access_points)` - a guaranteed `TypeError` every time it
  fires, permanently soft-locking the "new network"
  achievement-challenge type. Also a dead, unreachable duplicate
  `choose_random_challenge()` instance method (harmless, the real
  module-level function is the only one ever called). Findings
  presented and a fix-and-rebuild was suggested, but the user said to
  skip it and put it back on the list for a later pass - nothing
  built. A rewrite of `wifi_adventures.py` (below) was considered as
  a possible merge target for this plugin's achievement concept, but
  was built standalone instead since `achievements.py` itself isn't
  being touched yet - see `wifi-adventures-suite/NOTES.md`'s "Merge
  with achievements.py" section for the reasoning, which could be
  revisited once `achievements.py` eventually gets its own pass.

## Kept as-is (2)

- **`counter.py`** - no framework-misuse bugs found. Confirmed
  `self.options = dict()` in `__init__` is harmless (overwritten by
  the framework's real `.options` assignment in `load()`, which runs
  after `__init__`). `on_association`/`on_deauthentication` signatures
  are correct. Declares an unused `scapy` pip dependency - a cosmetic
  nit, not worth a rebuild on its own.
- **`IPDisplay.py`** - solid, defensively-coded plugin overall (uses
  `'key' in self.options` checks throughout rather than raw
  indexing). One minor, low-severity issue: a possible `IndexError`
  if the interface list is ever empty, already caught by the
  surrounding `try/except`. Not worth a rebuild.

## Fixed and moved to `plugins-wip`

- **`birthday.py`** - **-> `birthday-suite` (`BirthdayNG`)**. Three
  real bugs fixed: (1) `__defaults__` only set `enabled: False`, but
  `self.options["show_age"]`/`["show_birthday"]`/`["age_x_coord"]`/
  `["age_y_coord"]` were all directly indexed with no fallback -
  `KeyError` on load for any fresh config that didn't set every one
  of those keys explicitly. Now has real defaults for all four.
  (2) imports `dateutil.relativedelta` but `__dependencies__` declared
  `"pip": ["none"]` - fixed to declare `python-dateutil` correctly.
  (3) `load_data()` did `data["born_at"]` via direct indexing on
  `/root/brain.json` - a missing key previously left `self.born_at`
  silently at its `__init__` default (Unix epoch 0), displaying a
  wildly wrong 55+-year age instead of failing visibly. Now uses a
  safe `.get()`/try-except and displays "unknown" instead of a
  fabricated age.
  - **User-approved additions (2 of 3 proposed)**: a configurable
    `birthday_message` (default "Happy Birthday to me! I am {age} old
    today!", with `{age}` substituted) shown on the actual
    month/day match; and a self-healing `born_at` - if `/root/brain.json`
    has no `born_at`, the plugin writes a fresh timestamp to its own
    side file (`/root/birthday_ng_fallback.json`), never to
    `brain.json` itself, so a real `born_at` written there later
    always wins on the next load. An on-screen countdown-to-next-
    birthday (the third proposed addition) was explicitly declined
    and not built.
  - 25 tests, all passing against the real framework.
- **`fortune_cookie.py`** - **-> `fortune-cookie-suite`
  (`FortuneCookieNG`)**. There was no `__defaults__` dict anywhere in
  the class at all, yet `self.options['orientation']` and
  `self.options['enabled']` were both directly indexed with no
  fallback - `KeyError` on load/update for any brand-new install.
  Fixed with a real `__defaults__`. Also fixed the dead `orientation`
  option: the original's branches built byte-for-byte identical UI
  elements either way; `orientation` now genuinely changes the layout
  (vertical: two stacked elements; horizontal: one combined line).
  - **All 3 user-approved additions built**: timed rotation via a
    configurable `rotate_interval_seconds` (default 60) in
    `on_ui_update`, so the message actually changes while running,
    not just once at load; an expanded, configurable `fortunes` list
    (4 generic entries -> 20, in config.toml, with a code-level
    fallback to the defaults if configured empty); and an optional
    `fortune_command` (disabled by default) that shells out to a real
    `fortune`-style command, with full error handling (timeout,
    missing binary, non-zero exit, empty output all fall back
    gracefully to the configured list).
  - 19 tests, all passing against the real framework.
- **`spam_peers.py`** - **-> `spam-peers-suite` (`SpamPeersNG`)**.
  `__init__` did raw, unguarded `os.listdir("/root/peers")` with no
  existence check - since `Plugin.__init_subclass__` calls `cls()`
  immediately with **no try/except** anywhere in the loader, a
  `FileNotFoundError` here (e.g. a fresh install, or any device
  that's never had a peer detected yet) crashed the plugin's
  *loading* entirely, not just one hook. Fixed by moving all
  known-peers-loading logic into `on_loaded`, guarded with an
  existence check regardless. Also fixed `on_peer_detected`'s raw
  `peer.adv['identity']` indexing - the real `Peer` class explicitly
  guards against a malformed/null advertisement (`self.adv = {}`)
  with its own defensive `_adv_str()` accessor; direct indexing here
  crashed on exactly the case the framework itself guards against -
  fixed with `.get('identity')`, skipping/logging peers with no
  identity.
  - **All 3 user-approved additions built**: disk-persisted
    "greeted" peer tracking (a JSON state file, merged with any
    config-supplied `known_peers` on load, so a peer seen often isn't
    re-spammed every reboot); a configurable `regreet_after_hours`
    cooldown (default 168h/1 week, 0 = never re-greet) with a
    per-peer last-greeted timestamp, so a frequently-seen device can
    occasionally get greeted again instead of being silenced forever;
    and a jittered greeting delay (configurable min/max seconds, via
    a background timer, not blocking `on_peer_detected`) so the reply
    doesn't look like an instant bot response.
  - 22 tests, all passing against the real framework.
- **`Weather.py`** - **-> `weather-suite` (`WeatherNG`)**. Had a
  hardcoded OpenWeatherMap API key and a hardcoded location baked
  directly into the source, with zero config options - unusable for
  anyone but the original author, and the embedded key was exposed to
  anyone reading the file. `__dependencies__` also wrongly declared
  `"pip": ["scapy"]`. Fixed: real config options for `api_key` (no
  default - marked `>>> USER INPUT REQUIRED <<<`, README explains how
  to get a free key), `location`, and `units`; the fetch now runs on
  a throttled background thread instead of risking a live API call on
  every UI render tick; the original's bare `except:` was replaced
  with specific `RequestException`/parse-error handling.
  - **All 3 user-approved additions built**: a unicode weather-
    condition icon mapped from OpenWeatherMap's condition codes; a
    tracked last-updated timestamp, surfaced both on-screen (a
    staleness suffix on errors) and via a `on_webhook` status page;
    and a real metric/imperial/standard units toggle wired through to
    both the API call and the displayed unit symbol. One bug was
    caught and fixed during test-writing: `on_webhook` originally
    deadlocked (held its lock while calling a helper that also
    acquired the same non-reentrant lock) - fixed by releasing the
    lock first.
  - 34 tests, all passing against the real framework.
- **`wifi_adventures.py`** - **-> `wifi-adventures-suite`
  (`WifiAdventuresNG`)**. Full rewrite, not a bugfix - of the
  original's 6 "adventure type" hook-shaped methods, only 2
  (`on_handshake`, `on_unfiltered_ap_list`) are real pwnagotchi
  framework hooks. The other 4 are not real hook names this framework
  ever calls, and were permanently unreachable dead code (~500 lines)
  along with everything they alone called: a treasure-hunt minigame
  built on blocking `input()` calls, a wifi-auto-connect-via-
  cracked-password routine, and fake "stat boosts" on
  never-initialized attributes. Of the two real hooks:
  `on_unfiltered_ap_list` had the wrong signature (missing
  `access_points`); `on_handshake` called a helper with one argument
  against a two-argument signature - both guaranteed `TypeError`s. It
  also POSTed telemetry to a hardcoded personal IP - dropped entirely.
  The rewrite keeps the spirit (a fun on-screen achievement/streak
  tracker) built only around the two real hooks, both fixed:
  `on_handshake` tracks a handshake counter and a day-based streak
  (consecutive/same-day/gap logic) with a simplified 10-tier title
  ladder; `on_unfiltered_ap_list(self, agent, access_points)` now
  correctly tracks "new networks seen" against a persisted seen-BSSID
  set. State persists to JSON. The pointless "webhook pressed"
  log-only stub was replaced with a real HTML status page (handshake
  count, new-networks count, current title, streak).
  **Merge-vs-standalone decision**: built as its own standalone
  suite rather than merged into `achievements.py`'s concept, because
  `achievements.py` wasn't approved for work this round (the user
  said to skip it and revisit later) - merging now would have
  depended on an unaudited target and created an undocumented
  cross-suite dependency. Worth reconsidering consolidation once
  `achievements.py` eventually gets its own rebuild.
  - 44 tests, all passing against the real framework.

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

## Testing

144 tests total across the 5 rebuilt suites (BirthdayNG 25,
FortuneCookieNG 19, SpamPeersNG 22, WeatherNG 34, WifiAdventuresNG
44), all passing against the real cloned `jayofelony/pwnagotchi`
framework. None tested on real hardware yet.

## Still open

- No real-device test of any of the 5 rebuilt suites yet (display
  rendering, live peer/grid interaction for `SpamPeersNG`, a real
  OpenWeatherMap API key for `WeatherNG`, real handshake/AP events for
  `WifiAdventuresNG`).
- `achievements.py` remains on the list, decision deferred to a
  later pass.
- `spotify_now_playing.py` (Cluster 35) remains deferred, not
  addressed this pass.
