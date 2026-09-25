# PwnDoctor — Physical Validation Runbook (owner)

This is the **how-to** companion for the RC physical gate. `RC_READINESS.md` and
`RELEASE_CHECKLIST.md` are the authoritative check lists; this file gives the exact steps,
commands, and "what a pass looks like" so you can run the gate on your real
Jayofelony/Pwnagotchi Pi. Nothing here is a new feature — it validates the frozen RC.

> Golden rule: **start read-only.** Do the observe/dry-run checks first. Only do the
> failure-injection checks once you've confirmed the safe behavior, and always with a backup.

## 0. Before you start
1. Back up config: `sudo cp /etc/pwnagotchi/config.toml /etc/pwnagotchi/config.toml.premptest`
2. Install the exact tested package (see `INSTALL.md`) — `doctor.py` **and** `doctor_packs/`
   into `/etc/pwnagotchi/custom-plugins/`.
3. Record the environment for the compatibility row you'll add at the end:
   - `cat /proc/device-tree/model` (Pi model)
   - `cat /etc/os-release` (ID / VERSION_ID / BUILD_ID or IMAGE_ID)
   - `uname -r` (kernel) · `python3 --version` · Pwnagotchi version (from the UI/about)
4. Start in the safest posture:
   ```toml
   main.plugins.doctor.enabled = true
   main.plugins.doctor.autofix = "observe"
   main.plugins.doctor.dry_run = true
   ```
5. Watch the log in a second shell: `sudo tail -f /etc/pwnagotchi/log/pwnagotchi.log | grep -i doctor`

Open the Doctor page in the Pwnagotchi WebUI (the plugin's route, e.g. `http://<pi>:8080/plugins/doctor/`).

---

## A. Load & baseline (read-only)
| # | Check | How | Pass |
|---|-------|-----|------|
| 1 | Clean install + reboot load | install, then `sudo systemctl restart pwnagotchi` (or reboot) | log shows `[doctor] loaded vX (autonomy=observe, dry_run=True, packs=N)`; no traceback |
| 2 | WebUI opens | open the Doctor plugin page | page renders; header shows `autonomy`, `condition packs: 12`, `patient coverage`, `recurring` |
| 3 | Observe mode | leave a healthy device idle a scan cycle | findings (if any) show real outcomes; nothing is changed |
| 4 | Dry-run | with `dry_run=true`, trigger a fixable condition (see check 11 for a safe one) | outcome shows `would_fix`, and the action did **not** actually run |

## B. Safe healing & the autonomy dial
| # | Check | How | Pass |
|---|-------|-----|------|
| 5 | One safe automatic remedy | set `autofix="conservative"`, `dry_run=false`; soft-block Wi-Fi: `sudo rfkill block wifi`; wait a scan (or hit the page) | Doctor auto-runs `rfkill_unblock`; finding `rfkill_blocked` outcome `fixed`; `rfkill list` shows unblocked |
| 6 | Confirm-required hold | add `confirm_required = ["pwngrid_down"]`; stop the service: `sudo systemctl stop pwngrid-peer` | finding `pwngrid_down` outcome `awaiting_confirm`; service **not** yet restarted; page shows a "Confirm & apply" link |
| 6b | One-tap approve | click "Confirm & apply" (or open `?confirm=pwngrid_down`) | service restarts; outcome becomes `fixed` |
| 7 | Deny-actions veto | set `deny_actions = ["restart_service"]`; stop `pwngrid-peer` again | finding shows `needs_user`, service is **not** auto-restarted |
| 8 | Reboot-class gate | set `autofix="assertive"`; (config-invalid case, check 15) | `restore_config` shows `awaiting_confirm` even at assertive, unless `allow_reboot_actions=true` |

## C. Memory & persistence
| # | Check | How | Pass |
|---|-------|-----|------|
| 9 | Circuit breaker survives restart | force a fix to be attempted a few times, then `sudo systemctl restart pwnagotchi` | `/etc/pwnagotchi/doctor_breaker.json` exists; attempt budget is **not** reset to zero after restart (repeated failing fix eventually shows `gave_up`) |
| 10 | Patient Chart persistence, no scan churn | let it run several scans, then reboot | `/var/lib/pwnagotchi/doctor/patient.json` persists; its `updated_at` does **not** advance on every scan when nothing changed (SD-wear discipline) |
| 11 | Known-good checkpoint save/diff | on a healthy device open `?action=save_checkpoint`; later change something (enable a plugin) and reopen the page | first shows "checkpoint saved"; later shows a "Changed since known-good" diff |

## D. Condition-pack trust
| # | Check | How | Pass |
|---|-------|-----|------|
| 12 | Bundled provenance | confirm `doctor_packs/*.json` are installed (12 files) | Doctor loads them; remedy packs (rfkill/sd_readonly/wpa/config/handshakes) can act; page pack count = 12 |
| 13 | External explain-only default | drop a copy of a remedy pack (e.g. `rfkill_blocked.json`) into `/etc/pwnagotchi/doctor.d/`, keep `allow_pack_remedies=false` | the bundled one still wins (built-in id precedence); an external pack with a **new** id is loaded but explain-only (no auto-fix) |
| 14 | Malformed/oversized pack safe failure | put a truncated/garbage `.json` (and a >128 KB file) in `/etc/pwnagotchi/doctor.d/` | Doctor logs `condition pack skipped: … : <reason>` and keeps running; no crash |

## E. Failure-injection (do last, with backups)
| # | Check | How (reversible) | Pass |
|---|-------|------------------|------|
| 15 | Invalid config case | temporarily add a TOML syntax error to a **copy** you point `config_path` at (do **not** corrupt the live boot config) | `config_invalid` detected; with a `.doctor.bak` present, `restore_config` offered/held per gate |
| 16 | Radio / monitor failure | `sudo rfkill block wifi` (and/or start wpa_supplicant on the capture adapter in a lab) | `rfkill_blocked` / `no_monitor` / `wpa_supplicant_hijack` detected; wpa fix **blocked_guard** if that iface carries your uplink |
| 17 | Read-only / media guard | (optional, risky) simulate SD errors or a read-only root in a lab image | `sd_readonly` detected; `remount_rw` is **blocked_guard** when kernel SD I/O errors are present (media_ok guard) |
| 18 | Missing verification evidence | make a fix run where the verify signal can't be re-read | outcome is `executed_verification_unknown`, never a false `fixed` |
| 19 | Optional command absent | test on a unit without `vcgencmd`/`iw`/`journalctl` | those probes report unknown/unavailable; Doctor degrades cleanly, no crash |

---

## Recording the result
1. For **each** row: note pass/fail + any log excerpt.
2. On a clean pass, add a `physical_validated` row to `COMPATIBILITY_MATRIX.json` for the **exact**
   Pi model + image/version + kernel + python you recorded in step 0.3.
3. On a failure: **do not soften the label.** Keep the honest evidence, file the defect, let us fix
   it, rebuild a fresh tested artifact, and re-run the failed checks.
4. Then follow `RC_READINESS.md` → "Standalone repository move" to freeze/tag/publish.

Restore your config when done: `sudo cp /etc/pwnagotchi/config.toml.premptest /etc/pwnagotchi/config.toml`
