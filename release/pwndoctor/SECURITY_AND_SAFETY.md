# PwnDoctor v1 security and safety model

## Trust classes

### Core runtime
`doctor.py` is first-party executable code.

### Bundled Medical Library
`doctor_packs/` ships in the reviewed release and may retain mappings to existing allow-listed
actions. Every normal policy/guard/verification gate still applies.

### Owner/community packs
`/etc/pwnagotchi/doctor.d/` is explain-only by default. Explicit owner opt-in can expose only
actions that Doctor already compiles.

### Cached catalog
`catalog_dir` is **always explain-only**. The optional fetch tool requires HTTPS plus a pinned
SHA-256. Hash/signature provenance proves content/publisher identity only; authority delta is
always none.

### Specialist providers
`pwndoctor/provider/v1` snapshots contribute fresh evidence and explain-only findings. They
cannot define remedies. Core-collected evidence has precedence over provider values.

## Treatment gates

A mutation can be blocked/reduced by:

- no remedy / unavailable action;
- low confidence;
- owner condition opt-out;
- owner action veto;
- Standing Orders/tier;
- root-cause downstream suppression;
- named safety guard;
- recovery posture;
- poor verified per-device efficacy;
- confirm-required/reboot policy;
- persistent circuit breaker;
- dry-run;
- action failure;
- verification failure/unknown.

The machine-readable treatment decision trace records which gate decided the outcome.

## Recovery posture

Storage I/O errors, read-only-root evidence and invalid-config crash loops trigger a conservative
recovery posture. Mutation requires explicit owner confirmation. Recovery never expands authority.

## Verification

Unknown stays unknown. An action is not called fixed merely because a command returned success.

## Patient Chart

Patient Chart v2 is bounded, atomic/change-gated and migration-aware. An older Doctor refuses to
overwrite a future/newer chart schema it cannot understand.

## Provenance and signatures

A hash can prove byte equality. A signature can prove publisher identity under a verifier's
trust policy. Neither grants a new action, bypasses Standing Orders or changes trust class.

## Support data

Support bundles and status contracts intentionally avoid unnecessary personal/network identity.
Redaction is defense-in-depth, not a promise that arbitrary input can never contain something a
user considers sensitive; inspect an archive before public sharing.
