# OpenAI → Claude: PwnDoctor Review, Patient Chart Model, and Release Recommendation
## 2026-09-24

Claude — this note is intended as a direct collaborator handoff after reviewing your current `doctor` v0.4 implementation, `DOCTOR_ROADMAP.md`, `BUILD_LIST.md`, and the surrounding plugin suite on `claude/happy-newton-60zxt8`.

Your Doctor work is strong. The recommendation here is not to replace its direction, but to harden and sharpen it into something releasable while preserving interoperability with Beastagotchi.

---

## 1. Strongest shared model: Doctor has a permanent Patient Chart

The best split may be:

### Doctor Kernel
Small, trusted, always-present logic:
- probe scheduling
- incident lifecycle
- evidence/confidence handling
- condition evaluation
- remediation policy
- circuit breakers
- verification
- audit

### Patient Chart
Persistent, device-specific memory about **this exact patient**:
- board/SBC model + architecture
- RAM/CPU/storage
- display/touch hardware
- Wi-Fi adapters + interface roles
- kernel/Nexmon/firmware versions
- Pwnagotchi version/build
- Bettercap/pwngrid versions
- enabled plugins + plugin versions
- configured providers/services
- known-good fingerprint(s)
- previous incidents
- recurring/chronic conditions
- remedy attempts + outcomes
- per-remedy efficacy on this device
- hardware-specific quirks already learned
- current backup/recovery state
- last successful health baseline
- capability/probe coverage

This is the information Doctor should keep 'on retainer.'

### Medical Library / Specialist Knowledge
Generic knowledge does **not** all need to live permanently in the Doctor source:
- condition packs
- runbooks
- display-specific diagnostics
- UPS-specific knowledge
- release-specific compatibility notes
- plugin-specific troubleshooting
- optional probe packs

These can be built-in, cached locally, or resolved from trusted sources when needed.

The key distinction:

> Keep the patient's history close. Fetch the textbook chapter when needed.

This seems like the cleanest answer to scaling Doctor without turning `doctor.py` into a giant encyclopedia.

---

## 2. Patient Chart should be evidence, not personality memory

Keep it technical and bounded.

Suggested persistent shape:
- `identity` — hardware/Pwnagotchi/build fingerprint
- `known_good` — one or more verified baselines
- `incidents` — compact lifecycle history
- `remedies` — attempts/outcomes/recurrence
- `quirks` — confirmed device-specific facts
- `coverage` — what Doctor can/cannot currently observe
- `recovery` — backup freshness and destinations

Do not let it accumulate unlimited raw logs. Logs/support evidence remain separate and bounded.

---

## 3. Recommended hardening before public v1.0

### A. Verification truth
If an action executes but the verification re-collection fails, outcome should be something like:

`executed_verification_unknown`

not `fixed`.

Unknown must stay unknown.

### B. Persist circuit breakers
Attempt budgets should survive service restart/reboot so Doctor cannot get trapped in:

restart → forget attempts → restart again.

### C. Action metadata richer than `safe|risky`
The binary tier is a good prototype but too coarse long-term.

Useful independent attributes:
- reversible
- destructive/data-loss potential
- persistent vs transient
- service interruption
- connectivity impact
- reboot required
- recovery dependency
- confidence requirement
- blast radius
- probation/verification requirement

Example: stopping `wpa_supplicant` is not universally safe if it provides the owner's management uplink.

### D. Storage-failure behavior
`remount_rw` should not be treated as generically safe when SD/media failure is suspected.

If MMC/ext4/I/O evidence indicates failing media, prefer:
1. reduce avoidable writes
2. preserve critical state to independent storage
3. collect evidence
4. only then consider broad write-heavy remediation

### E. Health score caution
A 0–100 score is attractive, but risks false precision.

Prefer primary states like:
`OK / ATTENTION / DEGRADED / ACTION_REQUIRED / UNKNOWN`

If a number is added later, make it a transparent summary index with visible components/confidence.

### F. Broad sensing, bounded execution cost
`read broad, act narrow` is excellent.

Refinement:

> sense broadly but boundedly; act narrowly and gated.

Cheap local probes can run often. Expensive/network-active/hardware-intrusive probes should be scheduled or on-demand.

---

## 4. Externalized condition packs should probably move earlier

Current roadmap targets external condition packs around v0.8.

Recommendation: introduce the **schema and loader seam earlier**, before Doctor gains many more hard-coded conditions.

Suggested sequence:

### v0.5
- reboot/crash-loop
- `wpa_supplicant` hijack + bounded treatment
- interface mismatch
- journald bloat
- debug-log-level
- verification truth hardening
- persistent circuit breaker groundwork

### v0.6
- Condition Pack v1 schema/loader
- Patient Chart v1
- provider/specialist health seam

### v0.7
- recurrence/flap detection
- remedy efficacy
- sanitized support bundle
- plain-language narrative

### v0.8
- cached/fetched specialist knowledge
- runbook registry
- plugin-contributed health providers

### v0.9
- sibling-plugin integration / one-Doctor hub

### v1.0
- physical Pi validation
- release hardening
- docs/examples/upgrade path

---

## 5. On-demand knowledge model

Doctor should not need every ailment at boot.

Resolution order can be:
1. built-in critical knowledge
2. cached local condition/runbook packs
3. installed plugin/provider health knowledge
4. local docs/readmes
5. trusted project catalog/repository
6. owner-approved external source

Potential classes:

### Knowledge Pack
Data only. Conditions/runbooks/explanations/version applicability. Lowest risk.

### Probe Pack
Read-only diagnostics. Bounded runtime/inputs, ideally isolated.

### Remedy Pack
Adds remediation recipe/action adapter. Downloading it grants **zero authority** by itself.

That last distinction is important.

---

## 6. Shared condition-pack schema is the cleanest Beast ↔ PwnDoctor interop

PwnDoctor and Beast Doctor do not need identical engines.

They can share neutral knowledge describing:
- condition ID
- schema/version
- applies-to versions/hardware
- required signals
- detect expression
- severity
- confidence
- symptom/cause
- runbook/deep links
- optional remedy
- verification
- causal relationships
- provenance

PwnDoctor maps canonical names to its collectors.
Beast maps the same names into StateRegistry/Signal contracts.

This lets one ailment definition serve both projects without coupling the implementations.

---

## 7. Sibling plugins should become Doctor specialists

Strongly agree with your 'Doctor becomes the hub' section.

Suggested terminology:

> one Doctor, many specialists.

Candidate specialist providers:
- `boot_post` → intake/POST
- `display_setup_helper` → display specialist
- `why_no_handshakes` → radio/capture specialist
- `captive_portal` → connectivity specialist
- `conflict_referee` → resource-collision specialist
- `sd_wear` → write-history/storage specialist
- `thermal_predictor` → thermal early-warning specialist
- `battery_historian` → power-health specialist

For plain Pwnagotchi, prefer either in-process registration or ephemeral snapshots under `/run/pwnagotchi/health.d/` rather than frequent writes under `/etc`.

---

## 8. Highest-value plugins for first physical validation

Recommended order:
1. `doctor`
2. `display_setup_helper`
3. `why_no_handshakes`
4. `captive_portal`
5. `conflict_referee`
6. `mesh_vpn_presence`
7. `stat_source_bridge`
8. `boot_post`
9. `sd_wear`

These test the most consequential seams: diagnosis, headless recovery, display bring-up, radio issues, connectivity, Theme Manager interop, remote access and storage health.

---

## 9. Recommendation: finish and release PwnDoctor soon

The owner feels PwnDoctor is already valuable enough that it should be finished, physically tested, and released rather than living indefinitely as an internal experiment.

I agree.

Suggested approach:

### Release Candidate sprint
- finish the v0.5 high-value ailment set
- harden verification semantics
- persist remediation/circuit-breaker state
- add Patient Chart v1
- add dry-run/read-only/confirm-required safety options
- run full off-Pi test suite
- physically validate on at least one real Jayofelony Pi
- validate one broken-config case, one monitor/radio case, one service-restart case, one connectivity case, and one storage-warning case
- write install/rollback/recovery instructions
- tag RC

Then gather real user evidence before expanding aggressively.

The Doctor is already distinctive enough to be useful publicly.

---

## 10. Relationship to Beastagotchi

Do not make the standalone PwnDoctor subordinate to Beast.

Keep it useful independently.

Beast should borrow/adapt:
- detect+treat lifecycle
- condition schema
- chronic/flap logic
- known-good drift
- Patient Chart ideas
- specialist consult model

Beast then adds its stronger platform pieces:
- canonical Signals
- Capability graph
- Action Broker
- Owner policy
- Recovery Vault
- blast radius
- transactional rollback
- Experience/Studio/Deep-Link integration

Both projects improve from the cross-pollination.

---

## 11. Final design sentence

> Doctor should permanently remember the patient, not permanently carry every medical textbook.

That seems to be the cleanest shared direction.