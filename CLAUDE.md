# CLAUDE.md — test-plugins

The **third-party pwnagotchi plugin audit**. This repo tracks every community plugin under
review, decides keep/remove/fix per cluster, and hands anything worth keeping to
`patrickato/plugins-wip` for a proper rebuild before it graduates to
`patrickato/complete-plugins`. Guidance for any AI or human working here.

## Source of truth

- `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md` — the live list. One bullet per plugin, by
  category. Status tags mark what's IN PROGRESS / moved to plugins-wip. **Always read the
  repo, not a summary, for current state.**
- `plugin-upgrade-proposals/` — one folder per reviewed cluster, each with a `NOTES.md`
  (full findings/bug writeup) and indexed in `plugin-upgrade-proposals/README.md`.
- `plugin-upgrade-proposals/reference-configs/` — one real upstream config per still-tracked
  plugin (keep in sync as plugins are removed/moved).

## The workflow — follow it exactly

1. **Review a cluster, present findings as a compact markdown table**, not long prose or
   numbered headings:
   `| Plugin | What it does | Issue found | Suggested action |`
2. **Get an explicit keep / remove / fix-and-move-to-wip decision before editing anything.**
   Even "do the next N fix candidates" authorizes starting the work, not skipping review —
   still show what each plugin does, the bug(s), and improvement ideas, with a real chance
   to decide per plugin.
3. **When the user names specific plugins to act on ("drop 3, 4, 6"), that covers ONLY those
   named.** It is *not* blanket approval to also build/fix the rest of the cluster, even ones
   previously tagged "fix and rebuild" or already shown in a findings table. Never infer
   approval for unnamed items from context, an ambiguous answer, or an earlier suggestion.
   Show the rest and wait.
4. **After a decision:** update `MASTER_PLUGIN_LIST.md` (edit/remove the bullet(s); add a new
   numbered "Group N" entry at the TOP of the "## Elimination log"); write/update that
   cluster's `NOTES.md`; update `plugin-upgrade-proposals/README.md`'s index; keep
   `reference-configs/` current; then commit + push (with the Co-Authored-By trailer).

## Rebuild requirements (when a plugin moves to plugins-wip)

- `config.toml` built from scratch, modeled on the jayofelony fork's real
  `pwnagotchi/defaults.toml` conventions (not generic), with explicit
  `>>> USER INPUT REQUIRED <<<` markers. Name it plainly `config.toml` (or the real
  extension) — never an `example`/`.example` suffix, except a dotenv template for a
  non-pwnagotchi standalone tool.
- Full docs: `README.md` (install/troubleshooting + requirements/dependencies) and
  `NOTES.md` (research/bug writeup).
- Real automated tests under `tests/`, run against the **real cloned jayofelony framework**
  where feasible — separate sandbox-verified from needs-real-hardware.
- Target hardware: Pi 4 + 3.5" TFT, jayofelony 64-bit image.
- See `plugins-wip/CONVENTIONS.md` for the cross-suite contract (config-section-name =
  file basename, `DEFAULTS`+`_opt()` because the fork ignores `__defaults__`, sibling
  lookups via config option, `bind_scope` for servers).

## Standing facts about this fork (verified)

- **The loader ignores `__defaults__`** — a plugin relying on it crashes unless every option
  is set. This invalidates many upstream plugins on sight.
- **Config section = plugin file basename**, case included.
- Many upstream plugins subclass a `BasePlugin` that doesn't exist on this fork, declare
  non-existent hooks, or import modules that don't exist here — common fatal defects to
  check for first.

## Offensive plugins

Any deauth/jam/targeting plugin must gate on an **explicit authorized-target allowlist
(BSSID/SSID), empty by default** — never physical/range assumptions. Offensive/Bluetooth
idea backlogs live in the top-level `*_IDEAS_*.md` docs; **nothing in them is approved for
building** without an explicit decision.

## Related repos

`patrickato/plugins-wip` (rebuilds in progress), `patrickato/complete-plugins` (graduated),
`patrickato/beastagotchi` (the platform these run alongside). All three have their own
CLAUDE.md.
