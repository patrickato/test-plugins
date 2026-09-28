# Notes: TTS / voice plugin cluster

**Status: `pwnassistant.py` and `voice_gamer.py` REMOVED. `pwnspeaker.py`,
`rss_voice.py`, `speak_to_me.py` KEPT.**

Despite being grouped as "voice" plugins on the master list, these
five do genuinely different jobs - not a straightforward duplicate
cluster, more a mixed bag under one loose theme. Sources: `pwnassistant.py`,
`pwnspeaker.py`, `rss_voice.py`, `voice_gamer.py` from
`itsdarklikehell/pwnagotchi-plugins`; `speak_to_me.py` from
`Sniffleupagus/pwnagotchi_plugins` (newly cloned for this cluster).

## 1. What each one actually is

1. **`pwnassistant.py`** - two-way voice control: listens via
   microphone, recognizes speech with Google's speech API, answers
   with `pyttsx3` TTS, checks Google Calendar. The only one of the
   five that *listens*, not just speaks.
2. **`pwnspeaker.py`** - one-way TTS announcer, speaks a line for
   nearly every pwnagotchi event hook, using `pyttsx3` plus the older
   `pico2wave` tool.
3. **`speak_to_me.py`** - also a one-way TTS announcer, same general
   idea as #2 but built on `espeak-ng`, with a worker-thread queue and
   a curated (not exhaustive) set of announced events.
4. **`rss_voice.py`** - not audio at all - replaces pwnagotchi's
   canned on-screen status *text* with RSS feed headlines. No speaker
   or mic involved; "voice" here means the personality's text lines.
5. **`voice_gamer.py`** - also not audio - "voice" refers to
   pwnagotchi's internal `voice.py` module (the code that generates
   personality text). Downloads a file from a URL and overwrites that
   core module with it.

## 2. `pwnassistant.py` - REMOVED, catastrophic if ever loaded

No `plugins.Plugin` subclass, no `on_*` hooks - not a real plugin.
Executes dangerous code at **module level** (i.e. the instant Python
imports the file, which is exactly what a plugin loader scanning a
folder does to check for a plugin class):

```python
SERVICE = authenticate_google()   # interactive OAuth flow, needs a
                                    # browser + credentials.json
print("Start")

while True:                        # infinite loop, blocks forever
    print("Listening")
    text = get_audio()             # blocks on microphone input
    ...
```

If this file is ever in a location pwnagotchi's plugin loader scans,
importing it would hang the entire agent process indefinitely at load
time - not an exception that gets logged and skipped, a permanent
freeze. Also contains a plain typo bug (`if prase in text:` instead of
`phrase` - `NameError`) and calls `subprocess.Popen(["notepad.exe",
...])`, a Windows-only binary, from what would be Linux code. Not
salvageable as a plugin without a full rewrite from scratch (would
need to become event-driven around `on_webhook`/a background thread
instead of blocking module-level code) - removed rather than
documented-as-fixable.

## 3. `pwnspeaker.py` - KEPT, but comprehensively broken as shipped

**Bug (pervasive):** nearly every event hook builds its spoken
sentence with plain `+` concatenation against a non-string value:

```python
# on_ai_training_start
body = "The AI has started training for " + epochs + " epochs."   # epochs is an int

# on_channel_hop
body = "I am running on channel: " + channel                      # channel is an int

# on_association
body = "I am sending an association frame to: " + access_point    # access_point is a dict

# on_wait / on_sleep
body = "Waiting for " + t + "seconds..."                          # t is a float

# on_wifi_update / on_unfiltered_ap_list
body = "...access points: " + access_points                       # access_points is a list

# on_handshake, on_deauthentication, on_peer_detected, on_peer_lost,
# on_cracked, on_free_channel, on_epoch - same pattern throughout
```

Every one of these raises `TypeError: can only concatenate str (not
"X") to str` the instant that hook fires. Since this covers almost
every hook that actually fires on this fork (the AI-only hooks
`on_ai_*` never fire here at all and are dead code regardless), this
plugin is effectively non-functional across nearly its entire
feature set as shipped.

**Fix pattern** (apply per hook, using `str()` or an f-string instead
of `+`):

```python
# before
body = "I am running on channel: " + channel

# after
body = f"I am running on channel: {channel}"
```

**Compatibility issue, separate from the bug above:** the plugin's
own `__help__` text instructs installing `pico2wave` from
`libttspico-utils_..._armhf.deb` / `libttspico0_..._armhf.deb` -
`armhf` is 32-bit ARM, incompatible with this 64-bit-only jayofelony
image outright. The plugin already initializes `pyttsx3` at module
level too (`engine = pyttsx3.init()`), and every hook calls
`engine.say()`/`runAndWait()` *and* the `pico2wave`/`aplay` combo
redundantly - the `pico2wave` half could simply be dropped entirely
(the `pyttsx3` calls already produce spoken output) rather than
chasing down a 64-bit-compatible pico2wave replacement.

**Net effect:** kept per broad-scope philosophy (not a hardware
problem, a code problem, and the underlying `pyttsx3` approach is
sound), but this needs a genuine pass through every hook to fix the
string-building, plus deleting the redundant/incompatible `pico2wave`
calls, before it does anything but throw errors.

## 4. `rss_voice.py` - KEPT, works correctly

No audio hardware needed - pulls RSS feed content via `wget` and sets
`ui.set("status", ...)` with it, replacing pwnagotchi's canned status
text. `logging.warn(f"...options = %s" % self.options)` looked
suspicious at first glance (same pattern that broke `pwnaware.py` in
Cluster 10) but is actually fine here - the f-string literally
contains `%s` as plain text (not consumed by the f-string itself),
so the subsequent `%`-format against `self.options` works correctly.

**Gap found:** `__defaults__` declares its feed URLs as flat dotted
keys:

```python
__defaults__ = {
    "feed.wait.url": "https://www.reddit.com/r/worldnews.rss",
    ...
}
```

but the code reads them as a nested structure:
`self.options["feed"][key]["url"]`. A flat key literally named
`"feed.wait.url"` never satisfies a nested lookup like
`self.options["feed"]["wait"]["url"]` - so these specific defaults are
a no-op. The plugin still works correctly if the user writes proper
nested TOML tables themselves (`[main.plugins.rss_voice.feed.wait]`
`url = "..."`), since TOML naturally parses dotted table headers into
real nested dicts - it's only the plugin's own fallback defaults that
are shaped wrong. Not fatal, just means feeds must be configured
explicitly rather than relying on the shipped defaults.

**Correction (see Cluster 18's project-wide `__defaults__`
correction):** this shape-mismatch is actually moot regardless of the
flat-vs-nested key issue - this jayofelony fork's loader never reads
`__defaults__` at all, correctly-shaped or not. Every feed must be
configured explicitly in `config.toml` either way; the flat/nested
mismatch above would only matter on an upstream fork that actually
merges `__defaults__` in the first place.

## 5. `voice_gamer.py` - REMOVED, security anti-pattern + real bugs

Downloads arbitrary content from a configured URL and overwrites
pwnagotchi's own core system module with it:

```python
response = requests.get(custom_voice_url)
...
os.system(f"sudo cp {temp_file_path} /usr/local/lib/python3.11/dist-packages/pwnagotchi/voice.py")
```

No validation of the downloaded content whatsoever before it gets
`sudo cp`'d over a file that the running agent imports. Whoever
controls that URL's response controls code that loads into the live
pwnagotchi process. This is a bad design even independent of bugs -
removed on that basis, not just for its code defects, which are also
real:

- Never imports `logging` anywhere in the file (only `os`, `requests`,
  `from pwnagotchi import plugins`) - every `logging.info(...)` call,
  including the first one in `on_loaded()`, raises `NameError`.
- `def on_unload(self):` is missing the `ui` parameter the framework
  passes to `on_unload(self, ui)` - would raise a `TypeError` on
  unload.
- The default `custom_voice_url` value is a local filesystem path,
  not a URL - confused/non-functional defaults even before considering
  the design problem.

## 6. `speak_to_me.py` - KEPT, clean and well-built

The best-designed of the five. Uses `espeak-ng` (modern, works fine
on 64-bit ARM, unlike `pico2wave`), a background worker thread with
an `Event`-based message queue (`_queue_message`/`_worker`) so
announcements never overlap and a busy worker just skips a redundant
message rather than queuing forever, and wraps the actual speaking
call in try/except. Only announces a deliberately curated set of
events (loaded, ready, deauth, handshake, peer found, sad, rebooting,
BLE device found, AI-ready/best/worst-reward - the AI ones being dead
on this fork but harmless) rather than every single hook. Correctly
coerces non-string values with `repr()` where needed (e.g. `"Best day
ever %s" % repr(reward)`). No bugs found.

**Gap found:** no `__dependencies__` attribute at all (not even the
usual unused `scapy` boilerplate most of this project's plugins
carry) - `espeak-ng` (the actual runtime dependency, an apt package)
isn't declared anywhere. Minor, easy to fix if this is ever
distributed (`__dependencies__ = {"apt": ["espeak-ng"]}`).

## Dependencies (kept plugins)

`pwnspeaker.py`: `pyttsx3` (pip, already implied by import; not
declared in `__dependencies__` either - another gap), plus a working
audio output device (DAC hat, USB soundcard, or BT headset per its
own help text) - once the `pico2wave` calls are removed per the fix
above, `pico2wave` itself is no longer needed at all.
`rss_voice.py`: `feedparser` (pip - already self-installs via a
try/except import block at the top of the file if missing), `wget`
(apt, standard on Debian). `speak_to_me.py`: `espeak-ng` (apt, not
declared - see gap above) plus an audio output device.
