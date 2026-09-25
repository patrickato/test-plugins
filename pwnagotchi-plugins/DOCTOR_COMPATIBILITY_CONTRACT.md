# PwnDoctor Upstream Compatibility Contract
## Draft v1 — 2026-09-24

This contract defines how PwnDoctor reasons about future Jayofelony/Pwnagotchi changes without assuming that a new image is compatible merely because the plugin still imports.

## 1. Compatibility fingerprint

Doctor records a privacy-light environment fingerprint in the Patient Chart:

- `pwnagotchi_version`
- `python_version`
- `architecture`
- `kernel`
- `os_id`
- `os_version_id`
- `os_build_id` / image id when available

This fingerprint is descriptive evidence, not a device identifier. It intentionally excludes hostname, MAC addresses, SSIDs, IP addresses, GPS and owner data.

## 2. Evidence levels

A version/environment may carry one of these evidence labels:

- `physical_validated` — exercised on real hardware/image against the release checklist;
- `ci_validated` — automated/off-Pi tests cover the relevant API/behavior but no physical claim;
- `community_reported` — reported working by users, not independently reproduced by maintainers;
- `unknown` — not yet evaluated;
- `known_incompatible` — a concrete incompatibility has been reproduced or documented.

Do not collapse these into a single vague `supported=true` flag.

## 3. Unknown upstream behavior

When Doctor encounters an environment outside known compatibility evidence:

1. Continue read-only diagnostics that rely on stable/available interfaces.
2. Do not assume missing evidence means healthy.
3. Keep owner data/runtime state intact.
4. Prefer `observe`/confirmation for actions whose assumptions may have changed.
5. Surface the fingerprint and the exact compatibility uncertainty.
6. Collect a support/compatibility bundle once that feature exists.

Unknown upstream does **not** mean the entire plugin must refuse to load. Capability/probe behavior should degrade independently where possible.

## 4. Compatibility packs

A future release may ship data-only compatibility knowledge that describes known upstream differences, such as:

- renamed/moved service units;
- changed config keys;
- changed plugin API hooks;
- image/kernel generation notes;
- known broken/remediated combinations;
- required migration/runbook links.

Compatibility knowledge follows the same trust rule as other Doctor knowledge:

> provenance can establish where a compatibility statement came from; it does not grant mutation authority.

## 5. `applies_to` schema discipline

Condition Pack v1 currently supports platform + Pwnagotchi version bounds.

Do **not** add kernel/image predicates speculatively.

When the first real compatibility pack cannot be expressed faithfully with the existing fields, add the smallest necessary predicate with tests and shared Claude/OpenAI review.

Likely future candidates, only if needed:

- exact/regex `os_id` + `os_version_id`;
- `os_build_id` / image generation;
- kernel version range/prefix;
- required capability/probe presence.

## 6. Upstream update policy

PwnDoctor does not automatically update Jayofelony/Pwnagotchi.

A future update-aware Doctor may:

- detect that a newer upstream release exists;
- compare current fingerprint to known compatibility records;
- explain migration/reflash implications;
- recommend backup/known-good steps;
- hold an update until the owner acts.

It must not silently convert itself into an upstream package manager.

## 7. Release matrix

Each PwnDoctor release should eventually publish a small matrix containing:

- PwnDoctor version;
- Jayofelony/Pwnagotchi version/image tested;
- Pi/SBC model;
- architecture;
- Python version;
- kernel/OS build;
- validation evidence label;
- notes/known limitations.

At RC time, rows remain `ci_validated` until the owner/tester completes the physical checklist.

## 8. Relationship to Beastagotchi

Beastagotchi may consume the same compatibility fingerprint and compatibility knowledge, but its platform profile/capability graph can make richer decisions.

Shared rule across both projects:

> Detect what changed, preserve what is still true, isolate what is uncertain, and never turn an unknown upstream state into an invented compatibility claim.