# Cluster 35: Notifications / Social / Webhooks

14 plugins from the master list's Notifications/Social/Webhooks
category, all previously untouched by any cluster review. Full real
source was read and cross-referenced against the real cloned
`jayofelony/pwnagotchi` framework for every one with locatable source.

## Already handled elsewhere (no new action)

`pwnspeaker.py`, `rss_voice.py`, and `speak_to_me.py` are duplicate
listings of plugins already fully reviewed under **Cluster 13
(TTS/voice)** - see that cluster's own NOTES.md for their findings
(`pwnspeaker.py` kept despite being comprehensively broken as shipped;
`rss_voice.py` and `speak_to_me.py` kept, the latter with no bugs
found). No new research or action was done on them here.

`Discord v3.0.1` and `TelePwn v2.0` are the *kept* survivors of an
early duplicate-elimination pass (**Group 2**, before per-cluster
review began) - `discord.py`/`discord_notify.py`/`pwng2discord`/
`pwnagotchi-discord-plugin` and `telegram.py`/`neonbot.py` were all
dropped in favor of these two. This review read the correct, kept
source files (WPA2's `discord.py`, module version `3.0.2`; and the
`wpa-2` directory's `telegram.py`, module version `0.2.2`), not the
earlier-dropped duplicates.

## Removed at the user's request

| Plugin | Real finding |
|---|---|
| `twitter.py` | `os.path.exists(...)` is called but `os` is never imported - guaranteed `NameError` on every attempt. Even fixed, it then calls `display.block_update(force=True)` as a context manager, and `block_update` doesn't exist anywhere in the real framework - confirmed via a full method dump of both `pwnagotchi/ui/view.py` and `pwnagotchi/ui/display.py`. The tweet-with-picture feature never worked as shipped. |
| `TelePwn v2.0` (`telegram.py`) | A large (1478-line), otherwise structurally sound remote-control bot (40+ commands: reboot/shutdown/kill/backup/screenshot/rot13/leet-speak/etc., correctly using the `python-telegram-bot==13.15` `Updater`/context API matching its declared dependency). Two real bugs: `last_session.started_at()` is called but `LastSession` has no such method or attribute anywhere (`started_at` is only ever a local variable inside the framework's own `LastSession.parse()`) - guaranteed `AttributeError` on every new session with handshakes; and even past that, `self.send_notification(msg)` is called but never defined anywhere in the file (confirmed via an AST-level scan of every `self.X()` call against every defined method - the only undefined one in the whole file). Separately, `on_agent` isn't a real hook on this fork at all (confirmed via a full grep of every `plugins.on(...)` call site in the real framework) - dead code, though harmless, since the real `on_internet_available` hook it was meant to trigger early still fires normally on its own. |
| `sound.py` + `sound/shutdown_button.py` | `sound.py`: no `__defaults__` for the required `sound-dir`/`text2speech-lang`/`text2speech-use` options (only `enabled` has one) - `KeyError` on the very first `on_loaded` call if unset; `on_cracked` isn't a real hook on this fork (dead code, confirmed via the same hook grep). `shutdown_button.py` isn't a pwnagotchi plugin at all - no `Plugin` subclass, no hooks - it's a standalone script for a specific RaspiAudio sound-card button, meant to be run from `rc.local`, gated on `RPi.GPIO` and a specific pin wiring. |
| `PwnSpotify` | No source locatable anywhere across any of the archives searched in this project. Record-only removal. |
| `mqtt_plugin.py` | `__init__` calls `self.client.connect("localhost", 1883, 60)` synchronously, hardcoded host, with no error handling - and since `Plugin.__init_subclass__` calls `cls()` with no try/except anywhere in the loader, an exception here is a genuine plugin-load-time crash risk, a more severe class of bug than a hook that merely fails at runtime. Also declares an unused `scapy` pip dependency, and its `on_unloaded` (wrong name/signature - the real hook is `on_unload(self, ui)`) never fires. |
| `slack.py` | `self.option["title"]` and `self.channel["channel"]` (both typo'd - should be `self.options[...]`) are undefined-attribute accesses that crash the send path; `__dependencies__` declares `scapy` instead of the actually-needed `slackclient` (`from slack import WebClient`). |
| `mastodon.py` | Its own docstring says "based on twitter plugin by evilsocket" - shares that lineage's pattern of doing real work (screenshot capture, `Mastodon.create_app()`) outside any try/except. An unset/default-empty `instance_url` (its own `__defaults__` sets it to `""`) reaches `Mastodon.create_app()` unguarded, which reasonably fails without ever being validated first. |
| `ntfy_msg.py` | Its own exception handler references `self._log`, which is not a real attribute anywhere on the `Plugin` base class (confirmed via grep of `pwnagotchi/plugins/__init__.py`) - the same "masked error" shape found elsewhere in this audit (MoreUptimeNG's `uiItems`, TouchUING's `if reverse:`): when something goes wrong, this raises a second, more confusing error instead of surfacing the real one. |

## Left on the list, decision deferred

`spotify_now_playing.py` - calls `pwnagotchi.Config()`, a class that
does not exist anywhere on this fork (`pwnagotchi.config` is a
module-level variable, not a callable class - confirmed via grep of
`pwnagotchi/__init__.py`), so `on_loaded` crashes before `self.sp`/
`self.song_lock`/`self.last_song` are ever set, which in turn means
every subsequent `on_ui_update` call also crashes (on the now-missing
`self.song_lock`). Also calls `ui.display.draw_text(...)`, an API that
doesn't exist on this fork - the real convention (confirmed against
every default plugin) is `ui.add_element(...)` in `on_ui_setup` plus
`ui.set(key, value)` in `on_ui_update`, not free-form drawing. There's
also a stray, redundant module-level `SpotifyNowPlaying()`
instantiation at the bottom of the file (harmless, since `Plugin` has
no `__init__` override to fail on, but shows a misunderstanding of how
`Plugin.__init_subclass__` already instantiates the class on import).
Comprehensively broken as shipped; would need a full rewrite. User
chose to leave this on the list rather than drop or fix it for now.

## Built and moved to `plugins-wip`

### `apprise-notify.py` -> `apprise-notify-suite` (`AppriseNotifyNG`)

The most severely broken plugin found in this cluster: `__init__`
references an undefined `title` variable - present in literally every
one of its ~30 methods (it implements almost every callback name that
has ever existed across pwnagotchi forks, most of which aren't real
hooks here at all: `on_ai_ready`, `on_ai_policy`,
`on_ai_training_start/step/end`, `on_ai_best_reward`,
`on_ai_worst_reward`, `on_config_changed`, `on_free_channel`, `on_wait`,
`on_cracked` are all dead code, confirmed via the hook grep). Since
`Plugin.__init_subclass__` calls `cls()` with nothing catching the
exception, this is a genuine load-time crash, not a "one hook breaks"
bug. Every method also references a `.wav` attachment file that's never
created anywhere, and blocks with `time.sleep(1)` directly in whichever
real-time hook triggered it.

Rebuilt around: only hooks confirmed real on this fork (`ready`,
`handshake`, `peer_detected`, `peer_lost`, `rebooting`, plus the mood
hooks `bored`/`sad`/`excited`/`lonely`/`grateful`/`angry`, all
individually toggleable via `events`); a background worker thread +
queue (Discord v3.0.1's proven pattern) so a notification never blocks
the hook that triggered it; a `min_interval_seconds` cooldown so a
burst of events doesn't flood out all at once; real screenshot
attachment via `agent.view().image()` (confirmed to actually work -
see the correction below); and `urls`/`config_path` read from
`config.toml` instead of a hardcoded `/home/pi/apprise-config.yml`.

### `Discord v3.0.1` -> `discord-suite` (`DiscordNG`)

Already the best-engineered plugin found anywhere in this whole audit -
a threaded worker queue, an expiring WiGLE location cache, HTTP
retry/backoff, thread-safe handshake deduplication. Its one bug:
`getattr(last_session, 'deauths', 0)` reads an attribute that isn't
real - the actual `LastSession` attribute (confirmed in the framework's
`pwnagotchi/log.py`) is `deauthed`. Since it used `getattr` with a
default instead of direct indexing, this never crashed - it just always
silently evaluated to 0, so the Deauths field never appeared in a
session report even when there were plenty. Fixed here, plus new
`disable_wigle_lookup` (skip the WiGLE dependency entirely),
`attachment_mode` (`"file"` vs `"json_only"`), and
`include_session_stats` (toggle the previous-session report
independently) options.

### `terminal2.py` -> `terminal-suite` (`TerminalNG`)

Genuinely useful (a real in-browser terminal via WebSSH2, reachable
from the pwnagotchi web UI), broken by two missing imports: `re`
(`extract_ip_address()` calls `re.search(...)`) and `time` (the polling
loop calls `time.sleep(5)`). Since a freshly-started systemd service
almost never reports "listening on" on its very first check, the
first-run verification loop reliably crashed on one or the other on
essentially every fresh install - caught by the framework's own
exception handling (this hook's crash doesn't take down the daemon),
but `self.ready` never became `True` and the "started successfully" log
line never appeared, even though the underlying `systemctl enable`/
`start` calls (which ran *before* the loop) likely still worked in
practice. Separately, the webhook iframe only rendered for two
hardcoded, author-specific IPs (`10.0.0.*`, `192.168.44.44`).

Fixed both imports; `_service_status_output()` now properly handles
`systemctl status`/`is-active` returning a nonzero exit code for an
inactive unit instead of letting a `CalledProcessError` propagate
uncaught; replaced the hardcoded IP allowlist with a configurable
`allowed_networks` CIDR list (default: the three standard private
ranges), matched with Python's real `ipaddress` module instead of
string-prefix guessing, and the page now says access is denied instead
of silently rendering empty.

### `Showerthoughts` -> `showerthoughts-suite` (`ShowerThoughtsNG`)

No source for this plugin was locatable anywhere across any of the
archives searched in this entire project - unlike every other plugin
here, there was nothing to fix or diff. Built from scratch: fetches
from r/Showerthoughts' public JSON endpoint on `on_internet_available`,
throttled by `refresh_interval_seconds`, filtered by `min_score` and
truncated to `max_length`, cached to disk (so a restart or a stretch
with no internet still has content to show), rotating on-screen on a
timer and optionally reacting immediately to personality-state changes
(`bored`/`lonely`/`sad`, configurable via `reactive_states`). Handles a
reddit 429 (rate limit) by logging and keeping the existing pool rather
than crashing or clearing it.

## A correction surfaced during this review

While building `AppriseNotifyNG`'s screenshot-attachment feature, I
confirmed `agent.view().image()` **is** a real, working call -
`agent.view()` returns the live `Display` instance (not a bare `View`),
and `Display` (in `pwnagotchi/ui/display.py`) subclasses `View` and
adds `.image()`, `.clear()`, and the various `is_waveshareXXX()`
hardware checks. Earlier in this same cluster review, `display.image()`
calls in `twitter.py`/`slack.py`/`mastodon.py` were initially described
as the crash point, based on checking `View` alone (which genuinely
lacks that method) - that was incomplete, since the real runtime object
is the `Display` subclass. `.image()` itself works fine on all three.
This doesn't change any of their dispositions (all three were already
dropped by user decision before the correction was found) - their real
crash points are as documented above (`twitter.py`: missing `os`
import, then a genuinely nonexistent `.block_update()` call;
`slack.py`: the `self.option`/`self.channel` typos; `mastodon.py`: the
unvalidated `instance_url`) - just noting it for the record since it
affects how those earlier findings should be read.

## Testing

All 4 builds have real automated sandbox test suites run against the
real cloned `jayofelony/pwnagotchi` framework:

- `apprise-notify-suite`: 21 tests (the `apprise` pip package itself is
  stubbed - no network access to install it in this sandbox - but the
  stub matches its public API shape closely enough to exercise all of
  this plugin's own logic).
- `discord-suite`: 24 tests, using the real `requests`/`urllib3`
  libraries (already available) with only the HTTP transport mocked.
- `terminal-suite`: 26 tests, using the real `flask` library, with
  `os.system`/`subprocess` mocked (no systemd in this sandbox).
- `showerthoughts-suite`: 29 tests, using the real `requests` library
  with only the HTTP transport mocked (no live reddit call).

All 4 suites pass clean, 100 tests total.

## Still open

- No real-device testing of any of the 4 builds yet (live Discord
  webhook delivery, an actual Apprise notification service, a real
  WebSSH2/systemd install, or a live reddit fetch) - see each suite's
  own README "Still open" section.
- `spotify_now_playing.py`'s fate remains undecided.
- The earlier-flagged `PWNAGOTCHI-CUSTOM-FACES-MOD`/
  `pwnagotchi_LCD_colorized_darkmode`/`pwnagotchi-fallout-faces-mod`
  scope question (Cluster 34) remains open and is unrelated to this
  cluster.
