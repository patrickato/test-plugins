# `doctor_packs/` — first-party bundled Medical Library

This directory is reserved for **first-party Condition Packs shipped in the same PwnDoctor release as `doctor.py`**.

Trust boundary:
- Packs here are part of the reviewed PwnDoctor release artifact.
- They may reference remedies because moving a built-in condition from Python into first-party JSON must not silently remove its existing treatment capability.
- They still cannot introduce arbitrary executable code or actions: remedies must resolve to an action already present in Doctor's `ACTIONS` allow-list, and all confidence, guard, Standing Order, confirm-required and circuit-breaker rules still apply.
- User/community packs do **not** belong here. Those go in `/etc/pwnagotchi/doctor.d/` and are explain-only by default.

Load precedence:
1. core Python conditions;
2. bundled packs from this directory;
3. user/external packs from `/etc/pwnagotchi/doctor.d/`.

Duplicate IDs are ignored after the first authoritative definition, so an external pack cannot shadow a bundled or core condition.

Each loaded pack receives runtime provenance metadata including `source_class` and SHA-256 of the exact JSON bytes.

Do not manually edit this directory on an installed device if you want the release artifact to remain reproducible; use `/etc/pwnagotchi/doctor.d/` for local customization.