# Pwnagotchi Plugin Ecosystem Audit

A full sweep of findable pwnagotchi plugins, checked against your actual
image, deduplicated, and sorted by confidence. Compiled 2026-09-28.

**Method note (read this before trusting a "known-good"):** Nobody except
the jayofelony team has run these against *this exact* build. "Known-good"
below means "ships with or is officially distributed for this image."
Everything else is a judgment call from source/README inspection, not a
verified install - treat "likely to work" as "worth trying first," not a
guarantee.

---

## 1. What you're actually running

Pulled directly from the jayofelony repos (not the old evilsocket docs,
which describe a different, mostly-dormant project):

| Property | Value |
|---|---|
| Maintainer / repo | [jayofelony/pwnagotchi](https://github.com/jayofelony/pwnagotchi) (branch literally named `noai`) |
| Current version | v2.9.5.8 |
| Base OS | Debian **Trixie** (Raspberry Pi OS Lite), via a jayofelony fork of `pi-gen` |
| Architecture | **64-bit (arm64) only** - 32-bit support was dropped in v2.9.5.7 |
| Python | **3.11+**, venv layered on system Python |
| bettercap | **jayofelony's own fork**, branch `pcapng`, built from source (not upstream, not version-pinned) |
| Handshake format | **`.pcapng`**, not classic `.pcap`, since v2.9.5.5 |
| AI/RL layer | **Fully removed** - no `numpy`/`stable_baselines3`/`gymnasium`, zero `on_ai_*` hooks anywhere in the codebase |
| Personality state machine | Still present (bored/sad/excited/etc, epoch tracking) - just no longer ML-driven |
| Plugin loading | Unchanged from original: `main.custom_plugins` path (default `/etc/pwnagotchi/custom-plugins/`), `Plugin` subclass, `on_*` hooks auto-wired, all classic hook names present and confirmed by signature |
| Plugin installer | New: `sudo pwnagotchi plugins install <name>` pulls from [jayofelony/pwnagotchi-torch-plugins](https://github.com/jayofelony/pwnagotchi-torch-plugins) - the closest thing to an "official" community plugin index for this fork |
| Bundled default plugins | `auto-update`, `auto_backup`, `bt-tether`, `example`, `fix_services`, `gpio_buttons`, `gps`, `grid`, `logtail`, `memtemp`, `ohcapi`, `pisugarx`, `pwncrack`, `session-stats`, `switcher`, `ups_lite`, `webcfg`, `webgpsmap`, `wigle`, `wittypi`, `wpa-sec` |

**Your hardware** (from what you've told me): Pi 4, hostname
`pwnagotchi.local`, a 3.5" MPI3501 TFT touchscreen (not a Waveshare
e-paper HAT), and no UPS/battery hat wired up. That's the filter for the
"hardware-dependent" category below.

**The three things that actually kill old plugins on this fork:**
1. Anything that touched the AI/RL model internals - gone, no landing spot.
2. Anything requiring 32-bit-only (armhf) binaries - this image is 64-bit only.
3. Anything hand-parsing raw `.pcap` bytes instead of shelling out to
   `hcxpcapngtool`/`aircrack-ng`/`scapy` - captures are `.pcapng` now, and a
   byte-level pcap parser will choke on the different container format.

No plugin in the census below advertises #1 or #2 by name. A few touch #3
and are flagged.

---

## 2. Confirmed dead / dropped outright

Small list, because "for sure broken" is a high bar without actually
running the code. These are dropped for concrete, source-backed reasons -
not vibes.

| Plugin | Why it's out |
|---|---|
| `evilsocket/pwnagotchi` bundled: `onlinehashcrack.py`, `paw-gps.py`, `net-pos.py`, `led.py`, `watchdog.py` | Superseded - jayofelony's image already bundles direct replacements (`ohcapi.py`, `gps.py`/`gpsdeasy.py`, `fix_services.py`) that are written for this exact fork. Installing the old evilsocket originals on top would just conflict with what's already running. |
| `dadav/pwnagotchi-custom-plugins` (whole repo, 28 files) | **Archived Feb 26, 2024.** Every plugin in it that still matters is re-hosted and actively maintained elsewhere (see duplicate table below) - use those copies, not this frozen one. |
| `evilsocket/pwnagotchi-plugins-contrib` (whole repo) | Official-adjacent but the evilsocket project itself is dormant. Same situation as above - mirrored (ZTube, a Gitea mirror) and largely re-hosted by more active maintainers; use the active copies. |

Everything else that looked shaky (archived-adjacent, thin READMEs,
low-activity personal repos) got sorted into "needs testing" or "needs
fixing" below rather than dropped, since I can't prove it's broken from
source alone.

---

## 3. Duplicate resolution

Where multiple plugins do the same job, here's what I kept and why. The
"dropped" side isn't bad code, just redundant - skip installing it unless
the kept option doesn't work for you.

| Function | Kept | Why | Dropped (redundant) |
|---|---|---|---|
| Basic GPS position/display | **bundled `gps.py`** (already on your image) | It's the baseline, zero install effort | `paw-gps.py`, `gpsdeasy.py` (jayofelony-torch) - same job, no added feature |
| Advanced/multi-device GPS | **[GPSD-ng](https://github.com/fmatray/pwnagotchi_GPSD-ng)** (fmatray) | Most active dev (112 commits), multi-device support, NTRIP/RTK - a real feature step up, not a reskin | `gps-plus` (crahan, built off an unmerged PR), Sliim's 9-file `gps_*` set, `pwnagotchi-plugin-gpsd` (kellertk), `gps_more.py` (Sniffleupagus) - all thinner rewrites of the same idea |
| Full wardriving log (all seen APs → WiGLE) | **[wardriver-pwnagotchi-plugin](https://github.com/cyberartemio/wardriver-pwnagotchi-plugin)** (cyberartemio) | Clean single purpose, actively maintained, does exactly the wardriving job without extra baggage | `theylive.py` (AlienMajik, same idea, bundled into a bigger multi-feature plugin), `f0xtr0t` (a fork of the already-bundled `webgpsmap.py`) |
| Discord integration | **Discord v3.0.1** ([wpa-2/Pwnagotchi-Plugins](https://github.com/wpa-2/Pwnagotchi-Plugins)) | Versioned, clearly the most feature-complete (pcap upload, location maps, session tracking) vs. the others being basically "post a message" | `dadav`/`evilsocket-contrib discord.py`, `LOCOSP/pwng2discord`, `charagarlnad/pwnagotchi-discord-plugin` (has an open unresolved README issue) |
| Telegram integration | **TelePwn v2.0** (wpa-2, same family as the Discord winner) | "Advanced control and notifications" vs. the others being simple one-way notifiers | `dadav`/`evilsocket-contrib telegram.py`, standalone `wpa-2/telegram.py` (their own earlier, simpler version) |
| Local backup with retention | **AutoBackup v2.0** (wpa-2) | Retention policy, versioned, same trusted repo family as the Discord/Telegram winners | `auto_backup_ng.py` - does the same retention/GC idea, less actively positioned |
| Handshake hash-format conversion | **`hashie-hcxpcapngtool.py`** (PwnPeter) | Explicitly updated for modern hcxtools + current hashcat formats - matters given this fork's `.pcapng` switch | plain `hashie.py` (older, unclear hcxtools-version assumptions) |
| Dictionary-crack driver | **pwnagotchi_fast_dictionary** (nothingbutlucas) | README states it directly: "improved version of quickdic.py" | `quickdic.py` |
| memtemp / system stats | **`memtemp-plus.py`** ([jayofelony/pwnagotchi-torch-plugins](https://github.com/jayofelony/pwnagotchi-torch-plugins) - adds CPU frequency) | It's in the *official* installer repo for this exact fork - highest trust tier available | crahan's separate `memtemp-plus.py` (same name, built off an unmerged upstream PR) |
| Crack-display password/XP novelty | **Sniffleupagus's `display-password.py`** (adds QR code) | Strict superset of the plain version | `evilsocket-contrib`/`dadav display-password.py` |
| Age/XP progression novelty | **`agev2.py` + `expv2.py`** (itsdarklikehell) | "v2" revisions of the maintainer's own earlier plugins | `age.py`, `exp.py` (v1s, same author) |
| Region/channel handling | **your own `RFComplianceGuide`** (already built, this repo) | You already have a compliance-focused version; `fix_region.py` (V0r-T3x) does a *different* thing (unlocks channels rather than correcting to your legal domain) - not a true duplicate, just adjacent. Worth knowing it exists, not worth installing alongside yours unless you specifically want the unlock behavior. | n/a - noted, not dropped |
| Handshake crack pipeline | **your own `ClaudeCrackAuto` / `HashFormatDetector` / `RuleMutationCrack`** (already built, this repo) | Same territory as `hashie-hcxpcapngtool.py`/`DiscoHash`/`pwnagotchi_fast_dictionary`, but yours are whitelist-gated to your own SSIDs, which none of the community versions are | n/a - noted, not dropped; community versions have no target-scoping at all, so treat them as less safe defaults for your setup, not strictly better |

Naming collision worth flagging on its own: **there are two unrelated
plugins both called `age.py`** - itsdarklikehell's XP/strength tracker
(superseded by their own `agev2.py` above) and AlienMajik's completely
different narrative "cyber-legend" prestige system. They are *not*
duplicates of each other despite the name - if you want AlienMajik's
lore version, you'll need to rename one of the two before installing both.

---

## 4. Hardware-dependent - not applicable to your current build

These aren't broken, they're just for hardware you don't have wired up
(you're on a 3.5" MPI3501 TFT, no UPS/battery hat, no confirmed
GPS/BLE/SDR/LoRa dongle). Skip this whole section unless you add the
matching hardware.

| Plugin | Needs |
|---|---|
| `pwnagotchi-plugin-pisugar2`, `pwnagotchi-plugin-pisugar3` (+ fork), `pisugarx.py` (bundled), `pwnagotchi-WittyPi4L3V7-plugin`, `wittypi.py` (bundled), `ups_lite.py` (bundled), LouDnl's UPS Lite gist, `mad_hatter.py` (AlienMajik - closest thing to a "works with any UPS" option if you do add one) | A battery/UPS HAT (PiSugar, WittyPi, UPS Lite) - you confirmed you're not wiring one up |
| `Pwnagotchi_Waveshare_2.66inch`, `Pwnagotchi-WS-V3-V4`, `Pwnagotchi-Waveshare-V3-Fix`, `Pwnagotchi-on-waveshare-v4`, `waveshare_v3_touch.py`, `pwnagotchi_LCD_colorized_darkmode` | A Waveshare e-paper HAT - you're running a different display (MPI3501 TFT) entirely |
| `buttonshim.py` | Pimoroni Button SHIM |
| `gpio_buttons.py`/`gpio_buttons_ng.py` (bundled variant exists already) | Physical GPIO buttons wired in |
| `bluetoothsniffer.py` (jayofelony-torch), `blemon_plugin.py` | A BLE-capable adapter |
| `adsbsniffer.py`, `skyhigh.py` | RTL-SDR dongle (adsbsniffer) or just internet access (skyhigh, via OpenSky API - actually usable without extra hardware) |
| `meshpwnstic.py` | A Meshtastic LoRa radio |
| `gsmfake.py` | Waveshare GSM/GPRS/GNSS Bluetooth HAT |
| `morse_code.py`, `led.py` (superseded, see above) | A status LED wired to GPIO |

One correction inside that table: **`skyhigh.py` doesn't actually need
special hardware** - it's an OpenSky Network API call, so it'd work on
your Pi as-is if you want aircraft-tracking novelty. Moved it here only
because it's thematically grouped with `adsbsniffer.py`, which *does* need
an RTL-SDR.

---

## 5. Likely to work - worth testing first

Actively maintained (recent commits, real star counts, not archived),
generic hook usage, no exotic hardware, no known red flag. This is the
"try these" list.

| Plugin | What it does |
|---|---|
| `pwnagotchi_GPSD-ng` (fmatray) | Multi-device GPS, NTRIP/RTK support (see dedup table) |
| `wardriver-pwnagotchi-plugin` (cyberartemio) | Full wardriving log + WiGLE upload |
| Discord v3.0.1, TelePwn v2.0, AutoBackup v2.0, GitHub_Backups, Pwny-WG, Pwny-Tailscale, web2ssh, WigleLocator ([wpa-2/Pwnagotchi-Plugins](https://github.com/wpa-2/Pwnagotchi-Plugins)) | Notification, backup, and remote-access family - actively maintained as one cohesive repo |
| `snoopr.py`, `neurolyzer.py`, `probenpwn.py` (AlienMajik) | Surveillance/tracker detection, MAC randomization + WIDS/WIPS evasion, aggressive capture tuning - all generic hook usage, no special hardware |
| `pwmenu` (newfpv) | Mobile-first field console - actively maintained (v1.4.2, 51 commits) |
| `Teraskull/pwnagotchi-community-plugins` (`autocrack.py`, `clock.py`, `display_version.py`) | Newer unification effort, 79 stars, looks like the most "cleaned up" community collection right now |
| `hashie-hcxpcapngtool.py`, `pwnagotchi_fast_dictionary` | See dedup table - your best community options for crack pipelines if you want an alternative to your own plugins |
| `DiscoHash` (flamebarke) | Convert-and-analyze pcap → 22000, posts to Discord - distinct enough from the crack-pipeline winners above (adds analysis + notification) to be worth keeping separately |
| `dashboard.py`/`dashboard2.py`, `tweak_view.py`, `screen_refresh.py`, `more_uptime.py` (itsdarklikehell / Sniffleupagus) | Cosmetic display tweaks - low risk even if something doesn't render right on your TFT |
| `envtune` (adi170-alt) | Environment-aware tuning (EMA smoothing, best-settings memory) - interesting given the AI layer is gone; this is a plugin-space substitute for some of what the old RL agent used to do |

---

## 6. Needs fixing before use - specific known issue

| Plugin | Issue | Fix needed |
|---|---|---|
| `pwnagotchi-http-module` (qLJB) | README explicitly targets the **Bookworm** image; you're on **Trixie** | Check paths/package names it shells out to before trusting it; low activity (10 commits) so don't expect upstream fixes |
| `monstart`/`monstop` (xfox64x) | Hardcoded interface names in the script | Edit the interface name to match your adapter before running |
| `pwnagotchi_GPSD-ng` (fmatray) | Needs GPSD **≥3.22** (3.25+ for RTK specifically) | Check your image's gpsd version before installing; upgrade gpsd if it's older |
| `charagarlnad/pwnagotchi-discord-plugin` | Maintainer's own open issue (#5) says the README is inadequate to set up from | Expect to reverse-engineer config from source - or just use the wpa-2 Discord v3.0.1 winner instead |
| `pwnagotchi-postinstall` (HugeFrog24) | Very low activity (3 commits, 2 stars), reads like a personal one-off script collection rather than a maintained plugin | Read the shell scripts fully before running anything from it - don't treat it as vetted |

---

## 7. Novelty / low-priority - works, purely cosmetic

Safe, low-risk, no functional dependency on anything about your setup.
Install if you want the flavor, skip with zero loss otherwise.

`clock.py`, `darkmode.py`, `PWNAGOTCHI-CUSTOM-FACES-MOD`,
`PwnagotchiCharacterPlugin`, `Pwan-Girl`, `Bat-Trinity`,
`pwnagotchi-fallout-faces-mod`, `christmas.py`, `fortune_cookie.py`,
`birthday.py`, `Weather.py`, `IPDisplay.py`, `miyagi.py`,
`Showerthoughts`, `rss_voice.py`, `speak_to_me.py`, `PwnSpotify`,
`achievements.py`, `counter.py`, AlienMajik's `age.py` (the lore
variant - see naming-collision note above), `Fancygotchi` (theme
framework - repo itself flagged "[In development]" by its own author,
so expect rough edges)

---

## Summary counts

| Category | Count (approx) |
|---|---|
| Confirmed dead/dropped | 3 repos (~30+ individual files, mostly superseded duplicates) |
| Duplicate groups resolved | 11 groups, 1 winner each |
| Hardware-dependent (not applicable to you right now) | ~20 |
| Likely to work, worth testing | ~20 |
| Needs a specific fix first | 5 |
| Novelty/cosmetic | ~20 |

Full source list and every repo cited lives in the research this doc was
built from - ask if you want the raw uncategorized census instead of this
filtered version.

---
*Compiled by Claude · 2026-09-28*
