# Upgrade proposal: `instattack.py` → `instattack_plus` (working name)

**Status: PROPOSED — not approved, not built.**

## What this replaces and why

`instattack.py` (itsdarklikehell/pwnagotchi-plugins, forked from
Sniffleupagus) reacts to bettercap events the instant they arrive —
`on_bcap_wifi_ap_new` triggers an immediate `agent.associate()`,
`on_bcap_wifi_client_new` triggers an immediate `agent.deauth()` —
bypassing the normal epoch-based wait entirely. Source review found:

- **No de-duplication.** If bettercap re-reports the same client as
  "new" (e.g. after a channel hop causes it to drop out of and back
  into bettercap's cache), the plugin will re-attack it every time,
  with no memory of having already acted.
- **No scoping of its own.** It relies entirely on the stock
  `personality['associate']` / `['deauth']` booleans and whatever
  filtering the core agent already does upstream — it adds nothing
  independently.
- **Depends on an unmerged upstream core PR** (evilsocket/pwnagotchi
  #1192, bettercap-event-forwarding) for its `on_bcap_*` hooks to fire
  at all. If jayofelony's fork doesn't carry that patch, the plugin is
  silently inert on its main logic path — no error, no warning, it
  just never triggers.
- **Minor bug:** the UI-name restore on unload assumes a fixed
  suffix length (`name[:-3]`), which can corrupt the displayed name if
  the format ever differs from what it expects.

The core idea — react the instant something appears, don't wait for
the epoch cycle — is legitimate and distinct from what other plugins
in this repo do. The problems are all fixable without changing that
core idea.

## Proposed scope

**In scope:**
1. **Verify the dependency first.** Before anything else, check
   whether jayofelony's fork actually forwards `on_bcap_*` events (or
   an equivalent). If not, this whole approach needs a different
   trigger mechanism - possibly `on_wifi_update` polling at a short
   interval instead of true event-driven hooks. This is a prerequisite
   finding, not just a config option - the plan branches depending on
   the answer.
2. **Add a TTL-based de-dup cache** (MAC or AP+client pair → last-acted
   timestamp) so a flapping device can't be re-attacked more often
   than a configurable minimum interval.
3. **Add its own `targets` allowlist**, on top of (not instead of) the
   existing personality-toggle check - defense in depth, matching the
   scoping principle used elsewhere in this repo, rather than relying
   solely on whatever the stock agent's whitelist enforcement happens
   to guarantee.
4. **Fix the UI restore bug** - store the original display name
   directly instead of slicing off an assumed suffix length.
5. **Make the throttle values configurable** (currently hardcoded
   0.3s for associate, 0.75s for deauth) rather than fixed in source.
6. **Add a `dry_run` mode**, same as the hulk-upgrade proposal, for
   verifying trigger behavior before it acts for real.

**Explicitly out of scope:**
- Rewriting pwnagotchi core to add the missing event-forwarding PR
  ourselves - that's a much bigger, separate decision (patching core
  behavior) and shouldn't be bundled into a single plugin's upgrade.
  If the dependency isn't present, the fallback is a different trigger
  mechanism inside this plugin, not a core patch.

## Open design questions (for discussion before build)

- If `on_bcap_*` events aren't available on this fork, is a polling
  fallback (`on_wifi_update`, checked every N seconds against a
  "seen before" set) an acceptable substitute, or does the instant-
  reaction character of the plugin become pointless at that point?
  This needs an actual check against the jayofelony fork's source
  before deciding - not a guess.
- Should the de-dup TTL be per-device or global? A short per-device
  TTL (e.g. "don't re-attack this MAC for 10 minutes") seems more
  useful than a single global cooldown across all devices.
- Should `targets` here mean "only ever act on these SSIDs" (strict
  allowlist) or "never act on my own home network, act on everything
  else" (blocklist model)? The rest of this repo's active plugins use
  the strict-allowlist model - recommend staying consistent with that
  unless there's a specific reason not to for this one.

## Required tools / dependencies

None beyond a stock pwnagotchi + bettercap install, IF the
`on_bcap_*` events are available. If a polling fallback is needed
instead, no additional dependency either - just different hook usage.

## Proposed config

See `config-example.toml` in this folder. Not wired to real code yet.
