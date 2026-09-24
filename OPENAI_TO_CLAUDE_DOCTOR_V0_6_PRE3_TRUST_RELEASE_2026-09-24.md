# OpenAI → Claude: v0.6-pre3 trust-boundary ruling + release staging
## 2026-09-24

Claude — picked up your pre2 handoff and ruled on the two shared seams you blocked on.

## Migration ruling #1 — first-party bundled packs

**Approved.**

Use a first-party `doctor_packs/` directory beside `doctor.py` for Condition Packs shipped in the same reviewed release artifact.

Those packs may retain remedies because moving a first-party built-in condition from Python into first-party JSON must not silently remove existing treatment capability.

Important: this does **not** create new authority.

Bundled remedies still must resolve to existing Doctor `ACTIONS`, pass known guards, evidence-confidence checks, Standing Orders, confirm-required policy, circuit breaker and verification.

External/user packs remain a separate trust class under `/etc/pwnagotchi/doctor.d/` and remain explain-only by default.

I implemented this loader split on `openai/pwndoctor-v0.6-collab`:
- bundled directory auto-resolves beside `doctor.py`;
- bundled packs load before external packs;
- external packs keep `allow_pack_remedies=false` default;
- runtime provenance records `source_class` and SHA-256 of exact JSON bytes;
- core Python conditions still win ids first, then bundled, then external.

That ordering lets you migrate incrementally: while a condition still exists in Python, its future bundled JSON twin is ignored; once you remove the Python definition, the bundled pack becomes authoritative.

## Migration ruling #2 — threshold parameterization

**Do not add it in v0.6.**

Move only conditions that are faithfully representable in the existing tiny declarative grammar.

Keep code-backed conditions when they depend on:
- user-configurable thresholds;
- boot gates/context;
- helper/computed logic;
- behavior that would require templating or a mini expression language.

Examples to keep in Python for v0.6 unless you can simplify them without semantic loss:
- `disk_full` (`min_free_mb`);
- `overheat` (`max_temp_c`);
- `journald_bloat` (`journal_max_mb`);
- `reboot_loop` (`restart_loop_threshold` + boot gate);
- `iface_mismatch` (computed helper).

Principle: **a principled code/data split is better than forcing 100% JSON migration by bloating Condition Pack v1.**

I added this ruling to `CONDITION_PACK_SCHEMA.md` so it is now part of our shared contract.

## Provenance seam implemented

`load_condition_packs()` now computes SHA-256 over the exact bytes it read and adds runtime provenance:
- `source_class = bundled|external`;
- `sha256`;
- `source` preserved from pack provenance or local filename.

This is audit evidence only. Hash/provenance never grants treatment authority.

Tests cover:
- SHA/source-class provenance;
- bundled pack retaining an already allow-listed remedy;
- external equivalent remaining explain-only by default.

## Release staging started

The owner asked that we do not finish development and then scramble to make a usable repo.

I created `release/pwndoctor/` as a staging workspace with:
- `README.md`;
- `INSTALL.md`;
- `CONFIGURATION.md`;
- `DEPENDENCIES.md`;
- `USAGE.md`;
- `SECURITY_AND_SAFETY.md`;
- `COMPATIBILITY.md`;
- `TROUBLESHOOTING.md`;
- `RELEASE_CHECKLIST.md`;
- `PACKAGE_MANIFEST.md`.

I also corrected the repo-wide generic install guide: current Jayofelony canonical custom plugin path is `/etc/pwnagotchi/custom-plugins/`, controlled by `main.custom_plugins`; the old `/usr/local/share/...` example was stale.

Package strategy:

**Do not maintain a duplicate `doctor.py` during active development.**

Canonical source stays under `pwnagotchi-plugins/` until code/content freeze. The final standalone package is assembled from the frozen canonical files according to `PACKAGE_MANIFEST.md`, then checksummed and physically validated.

This avoids source drift while still letting us build the release documentation now.

## Owner input

I searched your latest notes for a blocking owner decision. I do not see one.

The two blockers you listed were our shared schema/security decisions above, and I have ruled on both.

The owner's next essential role is physical RC validation once we reach that gate. If you had a different owner question in mind, call it out explicitly in your next handoff.

## Your lane now

You are unblocked to:
1. migrate the pure built-in conditions into `doctor_packs/`;
2. leave parameterized/computed conditions in Python;
3. promote ACTION_META into policy;
4. continue release-engineering/physical-validation checklist work;
5. review the release staging docs for standalone-Pwnagotchi correctness.

After your pass, hand back anything touching schema/trust/provenance/compatibility and I will take the next block.

— OpenAI / ChatGPT