# PwnDoctor v1 physical validation runbook

This is the **only remaining gate** between software-complete `1.0.0-rc1` and stable
`1.0.0`.

Validate the **exact CI-tested archive**. Do not rebuild locally and assume it is equivalent.

## Before testing

1. Back up `/etc/pwnagotchi/config.toml`.
2. Install the exact RC archive with `sudo ./install.sh`.
3. Start with:

```toml
main.plugins.doctor.enabled = true
main.plugins.doctor.autofix = "observe"
main.plugins.doctor.dry_run = true
```

4. Record environment:
   - Pi model
   - Jayofelony/Pwnagotchi version/image
   - Python
   - kernel
   - OS id/version/build
5. Start the guided recorder from the extracted package:

```bash
python3 physical_validation.py --doctor doctor.py \
  --output physical-validation.json \
  --artifact-sha256 <exact-archive-sha256>
```

Resume at any time with `--resume`.

## Required v1 checks

The recorder is authoritative. It currently requires all of these to pass:

1. clean install + reboot load;
2. Doctor WebUI opens;
3. observe mode;
4. dry-run;
5. one conservative safe remedy;
6. confirm-required hold + approval;
7. treatment decision trace names the controlling gate/reason;
8. persistent circuit breaker survives restart;
9. Patient Chart v2 persists and v1 migration preserves history;
10. known-good save/diff + bounded generation history;
11. poor verified efficacy reduces automation to confirmation;
12. root-cause finding suppresses redundant downstream auto-treatment;
13. bundled pack provenance;
14. external pack explain-only default;
15. cached catalog explain-only;
16. fresh provider snapshot accepted and stale/invalid snapshot rejected;
17. malformed/oversized pack safe failure;
18. missing optional command degrades safely;
19. radio/monitor failure diagnosis;
20. invalid config diagnosis;
21. media/read-only guard;
22. recovery posture activates for questionable storage/config integrity;
23. missing verification evidence remains unknown;
24. narrative is coherent;
25. self-test + `pwndoctor/status/v1` are available/privacy-light;
26. sanitized support bundle is generated and manually inspected.

## Safe failure injection

Prefer reversible/lab-safe cases:

- `rfkill block wifi` / unblock;
- stop a nonessential monitored service and restore it;
- point `config_path` to a temporary malformed config instead of corrupting the live boot file;
- use test/provider files to verify stale/invalid provider handling;
- use dry-run for risky actions;
- do **not** deliberately damage an SD card.

For storage/media recovery behavior, use existing real evidence or a disposable/test image.

## Recorder workflow

Show status:

```bash
python3 physical_validation.py --output physical-validation.json --resume --summary
```

After every required row is `pass`:

```bash
python3 physical_validation.py --output physical-validation.json --resume --matrix-row
```

The tool refuses to produce a `physical_validated` row if any required item is pending,
failed or skipped.

## Failure rule

If any check fails:
- preserve the JSON validation record and relevant sanitized evidence;
- do not call the environment physically validated;
- fix the defect;
- rebuild a new CI-tested archive;
- rerun the failed check(s) on that exact archive.

## Stable promotion

After a clean physical pass:
1. add the generated matrix row;
2. set physical-validation state accordingly;
3. change `1.0.0-rc1` to `1.0.0` only;
4. run the full automated release gate again;
5. publish the stable archive and checksum.
