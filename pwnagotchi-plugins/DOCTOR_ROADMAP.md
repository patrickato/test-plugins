# Doctor Plugin — Design Notes & Roadmap

**Plugin:** `doctor` (P06) · **Current version:** v0.6.0-pre1 · **Last updated:** 2026-09-24
**Scope:** stock Pwnagotchi only (this is *not* the Beastagotchi Doctor; see §9 for the link).
**Status caveat:** everything below is source/CI reasoning + off-Pi tests. **Physical Pi
validation of the auto-fix effectors is still pending.**
**Collaboration:** this is now a Claude + OpenAI (ChatGPT) joint effort toward a public
Pwnagotchi release. Cross-notes live at repo root (`OPENAI_TO_CLAUDE_*`,
`OPENAI_CROSSPOLLINATION_*`, `CLAUDE_TO_OPENAI_*`). The shared interop contract is
`CONDITION_PACK_SCHEMA.md` (this folder).

**Division of labor (by demonstrated strengths):**
- **ChatGPT owns** the spec / data-model / security seams: Condition Pack schema evolution +
  loader hardening, Patient Chart evolution (incl. chronic/recurrence memory), canonical-key
  stewardship, guard *intent* vocabulary, and the future provenance/signing design (v0.8).
- **Claude owns** integration / content / release: migrating built-in conditions → JSON packs,
  the `ACTION_META`→policy engine, collectors/effectors + new ailments, the incident/verify
  loop, test coverage, plugin lifecycle/UI, CI + release engineering, and the physical-validation
  checklist. Offline-first is a Claude product decision.
- **Shared:** `CONDITION_PACK_SCHEMA.md` + the canonical-key naming pass; each reviews the
  other's changes before they land in `doctor.py`.

This document is the single pick-up point for the Doctor. It captures what it is now, the
design principles, and every idea/recommendation for where it goes next, so any contributor
(or AI) can resume without re-deriving the plan.

## 0. North star (end goal for the *Pwnagotchi* Doctor)

A single, trusted, **offline-first immune system** for stock Jayofelony Pwnagotchi. A small
**Kernel** (probe → diagnose → gated-treat → verify → remember) sits over a persistent
**Patient Chart** (what this device is + its incident/remedy history + learned quirks),
governed by owner **Standing Orders** (an autonomy dial the end user sets and can change at any
time), using a **Toolbox** of locally-available tools and a bundled **Medical Library** of
condition packs. It auto-heals the common beginner-breaking failures, gives clear step-by-step
guidance for the rest, and **never makes the device worse** (verify-or-rollback, persistent
circuit breakers, media-failure-aware, unknown-stays-unknown). It emits a one-click sanitized
support bundle and shares a neutral condition-pack schema with Beastagotchi — while staying
fully useful on its own, with **zero network required**.

> Doctor should permanently remember the patient, not permanently carry every medical textbook.
> Patient Chart says what is true · Standing Orders say what is permitted · Toolbox says what is
> available · Medical Library says what is known. *(shared framing with ChatGPT)*

---

## 1. What the Doctor is (identity)

The Doctor is the Pwnagotchi's **immune system**. Toggle it on and it autonomously scans
everything it can reach, diagnoses against a knowledge base of known ailments, **auto-fixes the
safe/reversible problems** and **gives step-by-step instructions for the rest**.

Its whole design rests on one deliberate asymmetry:

- **Sensing is broad and unlimited** — more visibility only ever helps. No downside to reading
  more.
- **Acting is narrow and gated** — every ability to *fix* is also an ability to *break*. So:
  allow-listed actions, evidence-confidence gates, verify-or-rollback, circuit breakers.

The thing that lets it scale toward "diagnose everything that's ever gone wrong" without
becoming a monster of if-statements is that **the knowledge is data, not code** (the condition
KB). Grow the data → grow the Doctor.

Growth happens on four axes plus one structural idea:
**See more · Fix more · Explain better · Remember & learn · Become the hub.**

---

## 2. Current state (v0.6.0-pre1)

**New in v0.6-pre1 (OpenAI/ChatGPT contribution, reviewed + integrated by Claude):**
- **Condition Pack v1 runtime** (`canonicalize_signals`, `eval_condition_expr`,
  `validate_condition_pack`, `pack_applies`, `condition_from_pack`, `load_condition_packs`):
  data-only boolean grammar over a first canonical namespace cut; bounded local/offline loader
  (`condition_dir`, default `/etc/pwnagotchi/doctor.d`, ≤128 packs / ≤128 KB each); packs are
  **explain-only by default** (`allow_pack_remedies=false`), and even when enabled can only call
  actions already in the allow-list — a downloaded pack gains **zero** execution authority.
- **Patient Chart v1** (`PatientChart`, default `/var/lib/pwnagotchi/doctor/patient.json`):
  bounded device identity + coverage + last status + known-good summary + a capped remedy-outcome
  history; atomic writes, chmod 600, **writes only on meaningful change** (SD-wear discipline).
- Web status line now shows autonomy, dry-run, loaded pack count, and Patient Chart coverage.
- **Claude follow-ups on top:** built-ins take precedence over same-id packs (a pack can't shadow
  a core condition); a shipped example pack (`doctor.d/system.memory_pressure_warn.json`) proves
  the loader end-to-end; CI broadened to run on all three working branches.
- Tests: **61** off-Pi unit tests (full repo suite green).

### Baseline carried from v0.5.0

**New in v0.5 (won't-work ailment pack + safety hardening):**
- Conditions added: `wpa_supplicant_hijack` (+ uplink-safe stop), `iface_mismatch`,
  `reboot_loop` (systemd `NRestarts`, boot-gated), `journald_bloat` (+ `vacuum_journal`),
  `debug_log_level`.
- **Verification truth:** an action that runs but can't be re-verified reports
  `executed_verification_unknown`, never `fixed`.
- **Persistent circuit breaker:** attempt budgets survive restart/reboot (`breaker_path`).
- **Safety guards:** `wpa_not_uplink` (won't stop wpa_supplicant if it carries your uplink),
  `media_ok` (won't remount rw when the SD is throwing I/O errors) → outcome `blocked_guard`.
- **Autonomy dial (Standing Orders):** `off / observe / notify / conservative (default) /
  assertive`, plus `dry_run` and a per-condition `disable_autofix` list; `on_config_changed`
  re-reads it live (end user can change settings at any time). Legacy `safe`→conservative,
  `all`→assertive.
- **`ACTION_META`** registry (reversible / destructive / interrupts_service /
  affects_connectivity / needs_reboot) — data seam for richer v0.6 policy.
- Tests: **50** off-Pi unit tests (full repo suite green).

### Baseline carried from v0.4.0

**Collectors (guarded, work on any Pi/screen):** services (`systemctl`), power/throttle
(`vcgencmd get_throttled` bits), disk free + **read-only-root**, `dmesg` signatures
(under-voltage, USB resets, OOM, SD I/O errors, wifi firmware), `config.toml` validity,
bettercap API reach, monitor interface (`iw`), rfkill, clock (year + NTP-sync), memory/swap
(`/proc/meminfo`), route/DNS, temperature, log signals, uptime.

**Knowledge base — 22 conditions:** sd_readonly, disk_full, log_bloat, bettercap_down,
pwngrid_down, rfkill_blocked, no_monitor, clock_wrong, ntp_unsynced, config_invalid,
plugin_crash_loop, handshakes_unwritable, undervoltage, throttled_now, overheat, low_memory,
swap_thrash, no_route, dns_broken, sd_errors, oom, usb_resets, wpa_sec_errors.

**Treat half — allow-listed actions:** restart_service, rfkill_unblock, set_time, remount_rw,
make_handshakes_dir, prune_logs, restore_config, quarantine_plugin. Tiered `safe`/`risky`;
circuit breaker; snapshot; **verified by re-collect + re-detect**; low-confidence findings are
**never** auto-fixed.

**Discipline (borrowed from Beastagotchi's Doctor/IncidentEngine):** evidence confidence
(high/medium/low); "unknown means unknown"; boot uptime-gating; incident open/resolve lifecycle
with a **black-box snapshot** at open time; causal chains; field status vocabulary
`OK / ATTENTION / DEGRADED / ACTION`.

**Known-good drift (v0.4):** save a device fingerprint (config hash, enabled plugins, `dpkg`
package versions, kernel, OS) as "known good"; later diff current-vs-known-good on demand →
"since your checkpoint, plugin X was enabled and bettercap upgraded 2.32→2.33."

**Tests:** 41 off-Pi unit tests.

---

## 3. Design principles (keep these)

1. **Sense broadly but boundedly; act narrowly and gated.** Cheap local probes can run often;
   expensive / network-active / hardware-intrusive probes are scheduled or on-demand. Never
   widen write access as casually as read access.
2. **Offline-first, network-optional.** A Pwnagotchi is often headless and offline by design.
   Everything critical must work with **zero network**; packs ship bundled + locally cached;
   fetching is a later, opt-in enhancement that never gates diagnosis or safe healing.
3. **KB as data.** Conditions are declarative; adding an ailment should not require touching the
   engine (goal: externalized condition-packs, §7 / `CONDITION_PACK_SCHEMA.md`).
4. **Verify, or report unknown.** Every action re-checks that the condition actually cleared; if
   it can't re-check, it says `executed_verification_unknown` — it never claims `fixed`. A push
   that leaves the device worse is worse than no action.
5. **Honesty.** `unknown` is a first-class value; confidence is explicit; a recommendation is not
   an executed action. Low-confidence (log-inferred) findings are explained, never auto-fixed.
6. **Do no harm.** Circuit breaker (persistent), snapshots, per-action guards, maintenance
   windows, dry-run, and a confirm-required tier keep autonomy from becoming a footgun.
7. **The owner is in charge.** Standing Orders (the autonomy dial + opt-outs) are the end user's,
   editable at any time; the Doctor's default posture is conservative.

---

## 4. Feature roadmap (the menu)

`⭐` = highest ROI / do first. `[safe]` read-only or reversible. `[risky]` needs gating.

### Axis 1 — See more (new sensors + conditions) — mostly `[safe]`
- ⭐ **reboot/crash-loop detection** — systemd restart counters / repeated boot markers.
- ⭐ **`wpa_supplicant` hijack** — the #1 "monitor mode won't work" cause.
- ⭐ **interface-name mismatch** — `main.iface` vs. actual (`wlan0`/`wlan1`/`wlan0mon`).
- **journald bloat** (`journalctl --disk-usage`); **debug log level in production**.
- **missing plugin dependency** (`ModuleNotFoundError` in log → "plugin needs package Y").
- **gpsd down while gps plugin enabled**; **bt-tether pairing lost**;
  **wpa-sec/OHC api_key missing but plugin enabled**.
- **protected-config drift** (main.iface, bettercap.handshakes changed);
  **clock in the future**; **RTC drift**; **kernel taint / module load failure**;
  **swap-on-SD anti-pattern**; **huge handshakes dir**.

### Axis 2 — Fix more (allow-listed remedies)
- ⭐ **stop the hijacking `wpa_supplicant`** `[safe]` — pairs with the sensor; fixes a huge class.
- ⭐ **vacuum journald** (`--vacuum-size`) `[safe]`.
- **re-establish monitor mode** (bounce iface / re-run mon setup) `[risky]`.
- **clear stuck lock/pid files** `[safe]`; **fix path permissions** `[safe]`;
  **set CPU governor** `[safe]`; **lower log level in config** `[risky]`.
- **schedule fsck on next boot** `[risky]`; **controlled reboot** `[risky, opt-in]`.
- ⭐ **confirm-required tier** — queue a fix for one-tap approval from web/phone (middle ground
  between auto and manual).
- **maintenance window** — don't auto-act during an active capture/expedition.

### Axis 3 — Explain better
- ⭐ **composite health score (0–100)** — glanceable + trendable.
- ⭐ **plain-language narrative** — stitch findings + causal chains + drift into one paragraph.
- **blast-radius preview before acting** — small hardcoded consumer map
  ("restarting bettercap pauses capture ~5s; nothing else depends on it").
- **runbook links per condition** (URL in each how-to).
- **face reaction** — the pet looks worried on `ACTION_REQUIRED`.

### Axis 4 — Remember & learn (local, weighted, no ML)
- ⭐ **remedy efficacy tracking** — "restarting bettercap cleared this 8/10 times" → reorder
  remedies / adjust confidence per-device.
- ⭐ **flap / recurrence escalation** — a condition that opens-resolves repeatedly is *chronic*;
  escalate from "restarted again" to "needs real attention" and stop blindly retrying.
- **health history + MTBF-style stats** (ties into streaks/achievements plugins).

### Cross-cutting
- ⭐ **one-click sanitized support bundle** — zip logs + redacted config + incident history +
  known-good diff, forum-ready. Huge for beginners.
- **notifications** — push on `ACTION_REQUIRED` (ntfy/Telegram/HA); daily health line via
  `daily_digest`.
- ⭐ **externalized `condition-pack` files** (§7) — community-extensible KB.
- **optional local-AI triage** (much later, gated) — advisory only, never acts outside the
  allow-list.
- **global safety knobs** — dry-run mode, read-only mode, per-condition autofix override,
  action budget/cooldown.
- **"Doctor, heal thyself" self-test** — report which sensors are available on *this* unit.

---

## 5. Become the hub (structural)

The Doctor should **consume the sibling plugins** rather than re-sense:
- `sd_wear` → chronic finding "SD ~40 days of writes left".
- `thermal_predictor` → pre-throttle warning feeds `overheat` earlier.
- `battery_historian` → "cell aging" chronic finding.
- `captive_portal` → its verdict replaces the Doctor's own DNS guess.
- `why_no_handshakes` → fold in / treat as a specialist consult.
- `conflict_referee` → display/GPIO collisions as findings.
- `boot_post` → the startup intake exam.

Result: not 39 scattered gadgets but **one instrument with one brain** reading all of them.
Mechanism: each sibling publishes a small JSON/state file the Doctor reads (or emits events the
Doctor subscribes to). The Doctor also publishes a canonical `doctor.state` others can read.

---

## 6. Version sequence (merged Claude + ChatGPT plan)

Reordered from the original so **hardening lands with v0.5** and the **pack loader + Patient
Chart move up to v0.6** (don't accumulate more hard-coded conditions before the seam exists).

- **v0.5 — "Won't-work" pack + safety hardening (DONE):** reboot/crash-loop, wpa_supplicant
  hijack (+ uplink-safe stop), interface mismatch, journald bloat (+ vacuum), debug-log-level;
  verification truth; persistent circuit breaker; media/uplink guards; autonomy dial + dry-run
  + per-condition opt-out + live reload.
- **v0.6 — Data-driven brain + memory** *(pre1 landed)*: condition-pack schema v1 + loader
  ✅ (ChatGPT); **Patient Chart v1** ✅ (ChatGPT); **remaining for v0.6 final:** refactor the
  built-in conditions into JSON packs (Claude), richer **action metadata drives policy** (extend
  the `ACTION_META` seam → Claude), chronic/recurrence counters in the Chart (ChatGPT).
- **v0.7 — Learn + explain:** recurrence/flap escalation; remedy-efficacy ranking (ranking
  only — never expands authority); **one-click sanitized support bundle**; plain-language
  narrative. (Confirm-required tier lands here too.)
- **v0.8 — Specialists on demand (offline-first, opt-in fetch):** cached condition/runbook
  registry; plugin-contributed health providers. Knowledge may be fetched; **remedies/actions
  gain zero authority merely by being downloaded.**
- **v0.9 — One Doctor, many specialists (hub, §5):** consume sibling-plugin snapshots via
  `/run/pwnagotchi/health.d/` (tmpfs, no SD wear).
- **v1.0 — RC + physical validation + release:** full off-Pi suite; physical Pi validation
  (broken-config, monitor/radio, service-restart, connectivity, storage-warning cases);
  install/rollback/recovery docs; tag RC → release.
- **Later (gated):** blast-radius preview, optional local-AI triage (advisory only, never acts
  outside the allow-list).

> Note on the health score: dropped as a headline number (false precision). Keep primary states
> + explicit confidence; if a number is ever added, make it a transparent index with visible
> components. *(ChatGPT §3E — agreed.)*

---

## 7. Externalized condition-pack schema (target for v0.8)

Conditions become loadable JSON data so users/community/Beast can contribute ailments without
patching the engine. Signals are referenced by canonical key.

```json
{
  "id": "wifi.wpa_supplicant_hijack",
  "severity": "high",
  "confidence": "high",
  "signals": ["proc.wpa_supplicant_running", "iface.monitor_present"],
  "detect": {"all": [
    {"key": "proc.wpa_supplicant_running", "is": true},
    {"key": "iface.monitor_present", "is": false}
  ]},
  "symptom": "wpa_supplicant is holding the Wi-Fi interface",
  "cause": "wpa_supplicant grabbed the adapter, so monitor mode / capture can't start",
  "fix": {"action": "service.stop", "args": {"unit": "wpa_supplicant"},
          "tier": "safe", "reversible": true,
          "verify": {"key": "iface.monitor_present", "is": true}},
  "howto": ["sudo systemctl stop wpa_supplicant",
            "Confirm iw dev shows a 'type monitor' interface."],
  "causal_chain": ["wifi.no_monitor"]
}
```

- `detect` is a tiny boolean tree (`all`/`any`, comparators `is`/`>=`/`<`/`contains`) over
  canonical keys — pure, testable, no code in a pack.
- `fix.tier` (`safe`/`risky`) + top-level `confidence` drive gating: auto-execute only
  `safe` + non-`low`; everything else is explain-only unless the owner escalates.
- `fix.verify` is the probation re-check; `causal_chain` collapses related findings.
- Ship the built-in 22 conditions in this format first, then allow user packs from a directory.

---

## 8. Real-world "ailment catalog" to keep filling

Prioritized by how often it hits beginners (from the Pwnagotchi community's common issues):
1. no monitor mode (wpa_supplicant / adapter / iface name) ← **top**
2. no handshakes (covered partly by `why_no_handshakes`)
3. bricked/won't boot after edit (config invalid, crash loop)
4. SD corruption / read-only / dying card
5. under-voltage / random reboots (power)
6. disk full (captures, logs, journal)
7. clock wrong → wpa-sec/TLS failures
8. display won't work (see `display_setup_helper`)
9. plugin crash takes down the UI (see `safe_mode_loader` idea in BUILD_LIST)
10. bettercap/pwngrid service down

Each becomes a KB entry with detect + confidence + fix-tier + how-to.

---

## 9. Relationship to the Beastagotchi Doctor (cross-project)

Beastagotchi has its own Doctor (`beastcore/doctor.py`, an **Explain** engine over a
dependency/provider graph) and a Black Box (`beastcore/incidents.py`). They are the
*complementary half* — explanation/causal/blast-radius vs. our detect+treat. A cross-pollination
note with 8 ranked recommendations + a shared condition-pack schema was written for that project
(external branch `claude/pwnagotchi-doctor-crosspollination`, file
`docs/Beastagotchi_Doctor_Pwnagotchi_CrossPollination_2026-09-24.md`). The condition-pack schema
in §7 is intentionally the same shape so a condition authored once can serve both — that shared
schema is the real interop opportunity between the two projects.

---

## 10. Resume checklist (pick up here)
- [x] **v0.5 pack shipped** — reboot-loop, wpa_supplicant hijack (+ uplink-safe stop), iface
      mismatch, journald bloat (+ vacuum), debug-log-level; verification truth; persistent
      breaker; guards; autonomy dial + dry-run + opt-out + live reload. 50 tests.
- [x] **v0.6-pre1 landed:** Condition Pack v1 runtime + Patient Chart v1 (ChatGPT), reviewed +
      integrated by Claude; built-in-wins guard, example pack, broadened CI (Claude). 61 tests.
- [ ] **v0.6 final:** do the joint canonical-key naming pass, then Claude migrates the built-in
      conditions into JSON packs and promotes `ACTION_META` to drive policy; ChatGPT adds
      chronic/recurrence counters to the Patient Chart.
- [ ] Toward RC: wire the confirm-required tier (v0.7), support bundle, then physical Pi
      validation (only the owner can do this — a scripted checklist ships with v1.0 RC).
