# PwnDoctor changelog / release notes

Versions below the horizontal rule are development pre-releases on the collaboration branch.
Physical-Pi validation is pending until a `physical_validated` row exists in
`COMPATIBILITY_MATRIX.json`; see `RC_READINESS.md` and `PHYSICAL_VALIDATION.md`.

## 0.7.0-pre1 — "explain better" (dev, resumes after RC freeze lifted by owner)

- **Plain-language narrative:** one human paragraph stitching status + auto-fixes + what-needs-you
  + causal chain + known-good drift. Shown on the Doctor page ("Summary") and reusable by other
  plugins via `Doctor.narrative()`.
- **One-click sanitized support bundle:** the Doctor page's "Download sanitized support bundle"
  writes a forum-ready `.zip` (report + redacted config + redacted log tail + incidents + Patient
  Chart summary + environment/drift). **Redaction** strips MACs, IPv4, emails, and secret/
  location/identity option values (api keys, SSID/BSSID, GPS, tokens, …). Written to
  `support_dir` (0600); the web handler stays a bounded request/response (writes to disk, returns
  the path — no streaming).
- New options: `support_dir`, `support_log_lines`.
- 102 Doctor tests / 364 repo green; package assembles as `pwndoctor-0.7.0-pre1`.

_Note: v0.6.0-pre4 remains the physical-validation RC below; v0.7 is additive dev on top. The
RC gate (`RC_READINESS.md` / `PHYSICAL_VALIDATION.md`) still applies to whichever commit is tagged._

## 0.6.0-pre4 — Release Candidate (physical-validation pending)

Doctor is now the Pwnagotchi's data-driven "immune system": broad-but-bounded sensing, narrow and
gated acting, offline-first.

**Diagnosis & knowledge base**
- Condition Pack v1: conditions are declarative JSON data over a ratified canonical signal
  namespace, with a tiny tri-state (true/false/unknown) `detect`/`verify` grammar.
- 12 first-party conditions ship as **bundled** Condition Packs; threshold/boot-gated/computed
  conditions remain Python-backed by design.
- Causal chains, incident open/resolve lifecycle with black-box snapshots, boot-grace gating,
  known-good checkpoint + drift ("what changed since it worked?").

**Trust & safety**
- Two pack trust classes: **bundled** (first-party, may carry allow-listed remedies) vs
  **external/user** (`/etc/pwnagotchi/doctor.d`, explain-only unless `allow_pack_remedies=true`).
  A downloaded pack gains **zero** execution authority.
- Evidence confidence gates auto-fix (low-confidence is explained, never auto-fixed).
- Per-action guards (`not_uplink`, `media_ok`); verify-or-report-unknown
  (`executed_verification_unknown` is never a false `fixed`); persistent circuit breaker that
  survives restart/reboot.
- `ACTION_META`-driven policy: `deny_actions` owner veto, and a reboot-class gate holding
  `restore_config`/`quarantine_plugin` for confirmation unless `allow_reboot_actions=true`.

**Autonomy (Standing Orders, owner-controlled, live-editable)**
- `off / observe / notify / conservative (default) / assertive`, plus `dry_run`,
  `disable_autofix`, and a **confirm-required** one-tap approval flow in the WebUI.

**Memory**
- Patient Chart: bounded per-device identity, diagnostic coverage, recurrence/chronic counters,
  and remedy-outcome history; atomic, change-gated writes (no scan-by-scan SD churn).
- Privacy-light compatibility fingerprint (version/arch/kernel/OS only — no
  hostnames/MACs/SSIDs/IPs/GPS/owner).

**Release engineering**
- Reproducible standalone package assembler (`build_release.py`) with `RELEASE_MANIFEST.json`
  (incl. per-pack id/version/SHA-256/has_fix inventory) and `SHA256SUMS`, all verified at build.
- Conservative `install.sh` (never edits `config.toml`); evidence-based `COMPATIBILITY_MATRIX.json`;
  CI runs the suite and assembles + archives the tested package.

**Verification:** 357 off-Pi tests green (95 Doctor-specific); package assembles and integrity-
verifies as `pwndoctor-0.6.0-pre4`. **Not yet physically validated on hardware.**

Built collaboratively (Claude + ChatGPT). See the root `*_TO_*` cross-notes for the full trail.

---

_Earlier pre-releases (pre1–pre3) and v0.1–v0.5 development history are summarized in
`docs/DEVELOPMENT_ROADMAP.md`._
