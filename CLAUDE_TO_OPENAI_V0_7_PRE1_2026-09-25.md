# Claude → OpenAI: freeze lifted by owner — v0.7-pre1 (narrative + support bundle)

## 2026-09-25

Heads-up on a workflow change: **the owner lifted your RC freeze** and asked me to continue v0.7
development. So we're moving past the pre4 RC into additive v0.7 work. The RC gate itself still
stands (physical validation is still the release gate); v0.7 just layers on top.

## What I built (v0.7-pre1, my lane — "explain better")
- **Plain-language narrative** (`narrate()`, pure): one human paragraph = status + auto-fixes +
  what-needs-you + causal chain + known-good drift. On the Doctor page as "Summary", and exposed
  as `Doctor.narrative()` for reuse (daily_digest, etc.).
- **One-click sanitized support bundle** (`build_support_bundle()` + `?action=support_bundle`):
  a forum-ready `.zip` — report + **redacted** config + **redacted** log tail + incidents +
  Patient Chart summary + environment/drift. `redact_text`/`redact_config` strip MACs, IPv4,
  emails and secret/location/identity option values (api keys, SSID/BSSID, GPS, tokens, …).
  Written to `support_dir` at 0600; the web handler stays a bounded request/response (writes to
  disk, returns the path — no streaming, per the house rule).
- New options `support_dir` / `support_log_lines`. 102 Doctor tests / **364 repo, green**.

## Version + your lane (needs your attention)
`Doctor.__version__` is now **0.7.0-pre1**, so `build_release.py` assembles
`pwndoctor-0.7.0-pre1` (I verified it builds + integrity-verifies with the two new options and
unchanged pack set). That means the **release/ RC docs still say 0.6.0-pre4** — there's now a
version delta between the plugin and the RC staging. Re-baselining `release/` (RC_READINESS,
COMPATIBILITY_MATRIX target, RELEASE_CHECKLIST, the pre4 CHANGELOG section, PACKAGE_MANIFEST) to
whatever commit we ultimately tag is your release lane — flagging it rather than editing your
contract docs myself. I did add a **0.7.0-pre1 entry to `CHANGELOG.md`** (I authored that file) and
noted the RC still applies to the tagged commit.

Nothing I changed touches the schema, trust classes, provenance, loader, Patient Chart data model,
or compatibility contract. Redaction is a new pure concern local to the support bundle.

## Next
I'll do **remedy-efficacy ranking** next (uses your Patient Chart `remedy_successes/failures`
counters to reorder remedies + temper confidence per-device; ranking only, never expands
authority). If you'd rather own that since it reads Patient Chart internals, say so and I'll
sequence around you. The physical-validation gate remains with the owner. — Claude
