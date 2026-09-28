# Upgrade proposal: `hulk.py` → `hulk_scoped` (working name)

**Status: PROPOSED — not approved, not built.**

## What this replaces and why

`hulk.py` (dadav/pwnagotchi-custom-plugins, archived repo, dead
upstream) puts the agent into an "always aggressive" mode via a tight
loop: every 5 seconds it calls the raw bettercap command
`wifi.deauth *`, which deauths every associated client on every AP
currently visible to bettercap. Source review (full writeup in the
parent conversation, condensed here):

- **No target scoping of any kind.** `main.whitelist` is never read.
  No RSSI floor, no blacklist, no cooldown, no channel filter.
- **No personality/mood integration.** Runs as its own timer loop,
  completely independent of the epoch-based pacing the stock agent
  and most other plugins respect.
- **Not built for safety at all** — its own `__description__` calls
  it a joke ("Hulk is always angry!"), and the repo has been archived
  since Feb 2024 with no further changes.

The core problem isn't the *idea* (a deliberately aggressive test mode
has legitimate use on an isolated bench) — it's that there's no way to
bound *who* it acts on. Any signal-reachable AP, including a
neighbor's network, gets hit exactly the same as an intentional test
target.

## Proposed scope

Keep the spirit — a fast, unconditional, no-epoch-wait attack loop for
deliberate stress-testing — but make "who it acts on" an explicit,
fail-safe allowlist instead of a wildcard.

**In scope:**
1. Replace `wifi.deauth *` with iterating bettercap's known AP/client
   list and calling `agent.deauth(ap, client)` only for APs whose
   SSID or BSSID appears in a `targets` list — same scoping principle
   already used by every active-attack plugin in this repo.
2. **Fail-safe default: if `targets` is empty, the plugin loads but
   takes zero action and logs a warning** — no accidental wildcard
   behavior from a blank config, unlike the original.
3. Also honor `main.whitelist` as a second, independent check —
   even if something is mistakenly added to `targets`, an entry also
   present in the stock whitelist is skipped. Defense in depth.
4. Keep the fast fixed-interval loop (configurable, not hardcoded to
   5s) as the distinguishing feature versus epoch-paced plugins — the
   whole point of a "hulk mode" is bypassing the wait, not the
   scoping.
5. Add a `dry_run` mode that logs exactly what it *would* deauth,
   without calling bettercap — for verifying `targets` matches what
   you expect before ever running it live.
6. Structured logging (timestamp, target, action) to a dedicated log
   file, not just the pwnagotchi journal.

**Explicitly out of scope (not carried over from the original):**
- The raw wildcard command itself — removed entirely, not just gated.
- The joke/flavor-text status messages — replaced with real state
  reporting.

## Open design questions (for discussion before build)

- Should `targets` accept BSSID, SSID, or both? (Recommendation: both,
  matching how `main.whitelist` itself works.)
- Should the loop auto-disable itself if `targets` is ever empty at
  runtime (config edited live), or only check once at `on_loaded`?
  (Recommendation: check on every loop iteration — config can change
  without a restart in some setups.)
- Is a fixed-interval loop still the right model, or should this
  instead hook `on_wifi_update` and act only when a listed target is
  actually seen in that update — arguably safer and less wasteful,
  but changes the "always-on aggressive loop" character of the
  original. Worth deciding intentionally rather than defaulting.

## Required tools / dependencies

None beyond what a stock pwnagotchi + bettercap install already has.
No external Python packages beyond the standard library and whatever
`pwnagotchi.plugins` / bettercap client library the agent already
uses.

## Proposed config

See `config-example.toml` in this folder. Not wired to real code yet -
this is the intended shape of the config once built, for reference and
for whoever picks this up to build against.
