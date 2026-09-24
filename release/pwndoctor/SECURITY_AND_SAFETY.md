# PwnDoctor security and safety model

## Trust classes

### Core runtime
`doctor.py` is executable first-party code.

### First-party bundled Medical Library
`doctor_packs/` ships in the same reviewed release. Packs are JSON/data-only and may retain existing first-party remedy mappings. They can reference only actions already compiled into Doctor's allow-list.

### User/community Medical Library
`/etc/pwnagotchi/doctor.d/` is a separate trust class. Packs are explain-only by default. Copying a JSON file onto the device does not grant it treatment authority.

## Treatment gates

A remedy may still be blocked by confidence, autonomy level, owner opt-out, confirm-required policy, named safety guard, circuit breaker, dry-run, missing action, or failed applicability.

## Verification

Condition Pack expressions use internal tri-state truth: true, false, unknown.

After a pack remedy:
- true verification → fixed;
- false verification → fix failed;
- missing/unreadable verification evidence → executed, verification unknown.

Unknown is never converted into success.

## Provenance

The loader computes SHA-256 over the exact bytes of each loaded JSON pack and records a `source_class` (`bundled` or `external`) in runtime provenance.

Future network-fetched catalogs may add expected hashes/signatures. A valid signature proves publisher provenance; it will not grant treatment authority by itself.

## Circuit breaker

Attempt history persists across restart/reboot so restarting Doctor cannot reset a failing repair loop.

## Media failure

Doctor must not treat a read-only root filesystem as permission to blindly remount read/write when kernel evidence indicates SD/media failure. Rescue/recovery takes precedence.

## Data handling

Patient Chart is bounded technical state, not an unlimited raw-log archive. The plugin should avoid unnecessary writes on SD-backed systems.