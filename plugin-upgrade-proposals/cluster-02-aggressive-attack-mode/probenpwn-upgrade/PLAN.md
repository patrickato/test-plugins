# Upgrade proposal: `probenpwn.py` → `probenpwn_scoped` (working name)

**Status: PROPOSED — not approved, not built.**

## Important framing difference from the other two proposals

`hulk.py` and `instattack.py` needed scoping *added* - they had
little to none. `probenpwn.py` (AlienMajik/pwnagotchi_plugins, active,
245 stars, versioned changelog) is different: it already has real
scoping (whitelist by MAC/hostname, RSSI floor, persistent blacklist
with auto-cooldown) and a genuinely well-engineered adaptive rate
limiter (per-AP token bucket keyed to live handshake success ratio).
Source review found no fundamental design flaw in its safety
mechanisms.

**This proposal is not "fix bugs," it's "reduce scope."** The
concern isn't that probenpwn.py works incorrectly - it's that it's
the most *capable and intrusive* of the three, and several of its
capabilities go beyond what "own SSIDs only" home-lab testing
strictly needs:

- **`maniac` mode self-activates** beacon flood, probe-response
  flood, auth flood, and assoc flood attacks based on its own
  internal heuristics (rolling success rate / channel density) - not
  a capability the user has to deliberately invoke each time, it can
  switch itself on.
- **WPS PIN extraction** shells out to `bully`/`reaver` - real,
  active brute-forcing against the AP, not passive capture. Currently
  gated by a single global `enable_wps` flag with no additional
  per-target restriction beyond that.
- **Enterprise/WPA3/PMF detection is purely offensive** - the plugin
  checks whether an AP is enterprise-protected only to decide which
  *extra* attack technique to layer on (PMF-bypass games, WPA3-
  downgrade attempts), never to exclude it from attack.
- It **rewrites `agent._config['personality']` live**, every few
  epochs, based on its own computed "mobility score" - not just
  reading pacing config, actively overwriting it.

## Proposed scope

A reduced-capability build, not a full reimplementation - reuse the
architecture and safety logic (whitelist/RSSI/blacklist/token-bucket),
remove or restrict the parts that add offensive capability without a
matching safety gate.

**Keep as-is (these are already well-designed):**
1. `ok_to_attack()` whitelist + RSSI + blacklist/cooldown gating logic.
2. The adaptive per-AP token-bucket rate limiter tied to live success
   ratio - this is a genuinely good piece of engineering worth
   preserving.
3. `stealth` and `tactical` modes.

**Restrict:**
4. **Drop `maniac` mode's self-activation entirely.** If a flood-style
   technique is ever wanted, it should require explicit, deliberate
   per-run invocation - never something the plugin switches itself
   into based on its own heuristics.
5. **Make WPS strictly per-target opt-in**, via a separate
   `targets_wps` list distinct from the general `targets`/whitelist -
   so WPS brute-forcing only ever runs against SSIDs explicitly
   listed for that specific purpose, not anything merely whitelisted
   for association/deauth. Global `enable_wps = true` alone should not
   be sufficient.
6. **Make the "quiet association" PMKID-solicitation techniques**
   (association-request harvesting, auth-frame harvesting,
   reassociation harvesting, RSN-bearing probe requests) individually
   opt-in per technique, default off, same as the original - but
   logged clearly enough at runtime to see exactly which technique
   fired and against what, for after-the-fact review.
7. **Bound the live personality-rewrite behavior.** Either log every
   value it changes (before/after) each time it rewrites
   `agent._config['personality']`, or - stronger option - make the
   rewrite itself opt-in (`allow_personality_rewrite = false` by
   default), so the adaptive rate-limiting logic still functions but
   doesn't reach into and modify the agent's own pacing config unless
   explicitly permitted.
8. **Enterprise/WPA3 detection becomes protective, not just
   offensive** - add a config option to skip attacking
   enterprise-flagged APs entirely, independent of whitelist status,
   default to skip.

**Explicitly out of scope:**
- Reimplementing the multi-armed-bandit channel selection algorithm
  from scratch - reuse it if the underlying code can be adapted
  directly (license/attribution permitting), don't rebuild for its
  own sake.
- Any change to how `bully`/`reaver` themselves work - this proposal
  only changes *when/against what* they're invoked, not how the
  external tools function.

## Open design questions (for discussion before build)

- Is dropping `maniac` mode entirely the right call, or would a
  version that *can* be manually invoked (not self-triggered) still
  be wanted? Recommendation: manual-only if wanted at all, never
  self-triggered.
- Should `targets_wps` require an entry to *also* be in the general
  `targets`/whitelist (i.e. "WPS only within an already-approved
  set"), or can it be fully independent? Recommendation: require
  both - WPS is the most intrusive capability here, it should need
  the most explicit approval, not less.
- Given how much of probenpwn.py's real value is the adaptive
  token-bucket rate limiter and whitelist logic specifically, is it
  worth reaching out to / crediting AlienMajik's upstream project
  directly (e.g. proposing these scoping options as PRs to the
  original) rather than maintaining a separate scoped fork? Worth
  considering before committing to a from-scratch build - upstreaming
  the safety options might get more real-world testing than a
  personal fork would.

## Required tools / dependencies

Same as the original: `hcxpcapngtool`/`hcxtools`, and (only if
`enable_wps` + a target is in `targets_wps`) `bully` and/or `reaver`.
`scapy` for raw frame construction (quiet-association techniques) and
sniffing (PMKID/SAE capture, if that portion is retained).

## Proposed config

See `config-example.toml` in this folder. Not wired to real code yet -
several keys here don't exist in the original probenpwn.py at all
(`targets_wps`, `allow_personality_rewrite`, `skip_enterprise`) since
they're new scoping controls this proposal adds.
