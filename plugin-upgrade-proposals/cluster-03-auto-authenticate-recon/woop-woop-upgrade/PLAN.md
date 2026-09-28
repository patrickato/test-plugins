# Upgrade proposal: `woop_woop.py` → `woop_woop_plus` (working name)

**Status: PROPOSED — not approved, not built.**

## What this replaces and why

`woop_woop.py` (credited `silentree12th`, "copied from c-nagy and
expanded with forrest's quick_rides_to_jail") auto-connects to
networks and, per its docstring, performs internal network recon.
Direct source review (pulled from the real repo) found:

- **Same load-blocking bug as `educational-purposes-only.py`:** line
  16 is a top-level `from pwnagotchi.ai.reward import RewardFunction`
  import. That module doesn't exist on this fork - it's removed along
  with the rest of the AI/RL layer. Unused anywhere else in the file.
  **This plugin cannot load on this image as shipped. Priority 0 fix,
  identical to the other plugin in this cluster.**
- **Different, broader targeting model than "known networks you
  configured."** It does NOT read a single `home-network` config
  value. `on_bored`/`on_sad`/`on_sleep`/`on_wait` all run the same
  logic: read `/root/handshakes/wpa-sec.cracked.potfile`, build a
  dict of `{ssid: password}` for every network with a cracked
  password in that file, and attempt to associate with ANY of them
  that's currently visible, at an RSSI floor of `-95` dBm (functionally
  no floor - that's close to the noise floor itself).
- This means its actual behavior is: **"auto-connect to whatever
  I've ever cracked a password for, regardless of whether I meant to
  connect to it."** For a lab where the only things ever fed into
  that potfile are your own deliberately-tested networks, this is
  fine. If anything else - even passively captured handshakes from
  networks that happened to be in range - ever gets cracked and lands
  in that file, this plugin would try to join it. That's a scope
  question, not a bug, and it's the main reason this one carries more
  caveats than `educational-purposes-only.py`.
- Same code-quality pattern as the other plugin in this cluster:
  fire-and-forget `subprocess.Popen()` calls with no return-code
  checks, unconditional MAC randomization + hostname spoofing, fixed
  `time.sleep()` chains instead of real state checks, module-level
  globals instead of instance attributes, the same stray-parenthesis
  bug in the `hostnamectl` command (copy-pasted from the same
  lineage).
- One additional oddity: it writes a plaintext copy of every network
  name it connects to into `/home/ips.txt`, appended forever, with no
  rotation/cleanup - a small but real information-hygiene issue if
  this file is ever backed up or shared without thinking about it.

## Proposed scope

**Priority 0 (blocking):**
1. Delete the dead `from pwnagotchi.ai.reward import RewardFunction`
   import - identical fix to the other plugin in this cluster.

**In scope after that:**
2. **Add an explicit `targets` allowlist that gates the potfile-based
   connect logic** - i.e. even if a network shows up cracked in the
   potfile, only actually attempt to connect if its SSID is also in
   `targets`. This turns "connect to anything I've ever cracked" into
   "connect to anything I've cracked AND explicitly approved," which
   brings it in line with the scoping principle used everywhere else
   active behavior happens in this repo, without losing the
   interesting part of the original idea (auto-reconnect based on
   crack results, not just a single hardcoded SSID).
3. Fix the stray-parenthesis hostname bug (shared with the other
   plugin in this cluster).
4. Add return-code checks on the critical subprocess calls.
5. Make MAC randomization / hostname spoofing configurable, default
   off, same reasoning as the other plugin - no reason to hide from
   your own router.
6. Either rotate/cap `/home/ips.txt` or drop it in favor of the
   structured log file pattern used elsewhere in this repo.
7. Same "implement real recon or drop the claim" decision as the
   other plugin - see that plugin's PLAN.md for the reasoning, applies
   identically here.

**Explicitly out of scope:**
- Changing how the potfile itself gets populated (that's controlled
  by whatever cracking/upload plugins are running, not this one).

## Open design questions (for discussion before build)

- Same core idea as `educational-purposes-only.py`'s upgrade - is
  "auto-reconnect based on what I've cracked" actually a feature you
  want, gated by an allowlist, or would you rather this whole
  potfile-driven trigger be dropped in favor of the simpler single-
  SSID model the other plugin already uses? They could be merged into
  one plugin with two trigger modes instead of two separate ones -
  worth deciding before building either further.
- Should `targets` here require an EXACT SSID match against the
  potfile entry, or should it also need to match the currently-visible
  AP's BSSID (in case two different networks ever share an SSID -
  unlikely at home, but the potfile is keyed by SSID string alone,
  which is a weaker identifier than BSSID).

## Required tools / dependencies

Same as the original: `macchanger` (optional per stealth toggle),
`wpa_supplicant`/`wpa_cli`/`dhclient`. Reads
`/root/handshakes/wpa-sec.cracked.potfile`, which depends on whatever
cracking/wpa-sec-upload plugin populates it - not a dependency of this
plugin itself, just an input it reads.

## Proposed config

See `config-example.toml` in this folder. Not wired to real code yet.
