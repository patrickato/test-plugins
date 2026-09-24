# OpenAI Review Notes — Claude Plugin Suite Cross-Pollination
## 2026-09-24

Scope: our-side notes for patrickato/test-plugins. Claude's working branch remains his designated workspace. This file lives outside that branch so ideas can be shared without overwriting collaborator work.

Reviewed:
- claude/happy-newton-60zxt8
- DOCTOR_ROADMAP.md
- BUILD_LIST.md
- README.md
- Doctor v0.4 implementation
- selected plugin implementations including mesh_vpn_presence, stat_source_bridge, why_no_handshakes, display_setup_helper, conflict_referee and sd_wear

## Strongest conclusions

1. Keep the plugin collection useful for plain Jayofelony Pwnagotchi. Do not reduce it to disposable Beast prototypes.
2. Use successful plugins as research implementations for Beast capabilities, Doctor probes, Choreography inputs and provider adapters.
3. Treat Doctor as one user-facing instrument with specialist probes/consults, not a collection of competing mini-doctors.
4. Externalized condition packs are the best direct interoperability seam between PwnDoctor and Beast Doctor.
5. Keep Claude's branch intact; use a separate review/integration branch before any merge to main.

## Doctor refinements

- Broad sensing should be bounded by cadence, cost, privacy and side effects.
- Replace a binary safe/risky label with richer action metadata: reversibility, data loss, connectivity impact, persistence, blast radius, reboot, privacy and confidence requirements.
- If a fix executes but verification fails to run, report verification_unknown rather than fixed.
- Persist circuit-breaker/remediation history across restarts.
- Remedy efficacy may rank suggestions or reduce repeated retries but must not automatically expand authority.
- A 0-100 health score risks false precision; prefer status + evidence confidence, or make any numeric index explicitly transparent.
- Use /run for ephemeral sibling-plugin health snapshots rather than creating frequent SD writes.

## Doctor Knowledge / Skill Cache idea

Doctor should not require every possible ailment, hardware quirk, upstream version and runbook in one permanent Python file.

Preferred model:
- small Doctor kernel
- built-in critical knowledge
- cached condition/runbook packs
- optional read-only probe packs
- separately governed remedy/action adapters
- trusted on-demand acquisition
- provenance/hash/version/applicability metadata
- offline cache with storage budget

User-facing metaphor: Doctor can 'consult a specialist'.

Examples:
- display issue -> load display knowledge/probe
- no-handshake issue -> load radio/Pwnagotchi condition pack
- unknown UPS -> load provider-specific health pack
- new Jayofelony release -> load compatibility pack
- plugin crash -> fetch verified local/upstream documentation metadata

Knowledge may be fetched broadly. Executable tools are fetched narrowly and never gain root/action authority merely because they were downloaded.

## Plugins with highest near-term physical-validation value

1. doctor
2. display_setup_helper
3. why_no_handshakes
4. captive_portal
5. conflict_referee
6. mesh_vpn_presence
7. stat_source_bridge
8. boot_post
9. sd_wear (validate as a write historian; avoid overstating remaining-life precision)

These collectively test the most valuable cross-project seams: diagnostics, headless help, display recovery, connectivity, Theme Manager bridging, remote transport and storage-health awareness.

## Plugin concepts that map cleanly into Beast

- doctor -> Beast Doctor detect/treat research
- boot_post -> Doctor startup intake / POST view
- display_setup_helper -> Display Doctor probe + Hardware Studio
- why_no_handshakes -> radio/Pwnagotchi specialist consult
- captive_portal -> connectivity Signal/provider
- conflict_referee -> Cohesion Lint / resource collision checks
- sd_wear -> storage write-history Signal (heuristic, not authoritative media-health score)
- thermal_predictor -> Resource Governor early-warning input
- battery_historian -> power history / capability health
- env_sensors / rtl433 / adsb -> Beast Senses providers
- mesh_vpn_presence -> overlay-network provider for BenchLink/Studio/Recovery
- stat_source_bridge -> Presentation Broker / Theme Manager adapter research
- achievements/streaks/fireworks/pet_quips/circadian -> Progression + Choreography + Personality research
- offline_reader -> Field Library provider
- ha_mqtt -> Beast Bus / external integration

## Tailscale / WireGuard

For plain Pwnagotchi the plugin remains useful. For Beast, treat these as replaceable connectivity providers rather than Doctor-owned features.

Possible capabilities:
- connectivity.overlay
- benchlink.remote
- studio.remote
- recovery.remote_vault
- companion.remote

Configuration-changing commands such as tailscale up should become explicit Actions/Transactions in Beast rather than incidental side effects of a status collector.

## Own plugin ideas / future doodle space

The existing PWNAGOTCHI_GAP_AND_PLUGIN_IDEAS_2026-09-24.md remains our backlog. New ideas can be added here first, then promoted to a dedicated roadmap when they mature.

High-value areas still worth exploring:
- exact framebuffer mirror + optional touch-coordinate overlay
- sanitized one-click support bundle
- config/schema linter before restart
- upstream API/version compatibility watcher
- recovery manifest / blank-SD rebuild auditor
- plugin callback profiler / instability detector
- local runbook registry
- first-boot/post-upgrade self-test
- headless recovery portal
- known-good fingerprint/change journal

## Project handling recommendation

Do a short, bounded plugin cross-pollination sprint now, then return primary focus to Beastagotchi.

Do not spend weeks polishing all 39 plugins before Beast v0.19 visual reconstruction moves again.

The plugin suite is strategically useful because it gives us inexpensive experimental implementations. Beast remains the main product and architectural authority.