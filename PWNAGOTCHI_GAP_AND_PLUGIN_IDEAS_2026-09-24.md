# Pwnagotchi Gap / Plugin Ideas
## Initial R&D backlog — 2026-09-24

Target context: current Jayofelony Pwnagotchi, with special interest in Pi 4 but
ideas should remain portable where practical.

This is an idea/roadmap document, not a claim that no similar community code can
exist anywhere. The initial scan compared the current Jayofelony built-in plugin
set and current upstream issue patterns. Dedicated, polished equivalents for
several items below were not obvious in that scan.

The focus is reliability, diagnostics, recovery and usability.

---

# Priority A — unusually high leverage

## 1. PwnDoctor

A first-class Pwnagotchi health/triage plugin.

Read-only first.

Potential checks:
- Pwnagotchi/bettercap/pwngrid service state;
- wlan0 / monitor interface existence;
- monitor-mode health;
- driver/Nexmon versions;
- supported vs currently used channels;
- regulatory-domain evidence;
- interface/channel mismatch;
- Internet route vs actual DNS resolution;
- Bluetooth tether state;
- USB gadget addressing/routes;
- package half-configured state;
- filesystem read-only state;
- disk/free-space pressure;
- recent MMC/ext4/I/O errors;
- thermal/throttle state;
- plugin import/load errors;
- framebuffer/touch presence;
- time/date sanity.

Output:
- OK / attention / critical;
- exact evidence;
- likely cause;
- safe next diagnostic step;
- matching local runbook;
- optional sanitized support bundle.

Why this matters:
current upstream reports still include problems such as USB gadget connectivity,
Bluetooth tether DNS, monitor/radio-driver recovery and update/package failure
states. These are often diagnosable but presently require SSH/log expertise.

Possible later Beast tie-in:
PwnDoctor can become a provider/source for Beast Doctor rather than being
discarded.

---

## 2. PwnSupport Bundle

One-click sanitized diagnostic archive for Discord/GitHub/support.

Include, with redaction:
- Pwnagotchi/image/version/kernel;
- Pi/hardware model;
- package versions;
- plugin list + enable state;
- service status;
- relevant journal excerpts;
- interfaces/routes/DNS state;
- Wi-Fi/monitor/driver information;
- display/framebuffer/touch inventory;
- disk/filesystem/thermal state;
- config schema/keys with secrets removed;
- recent crash/reboot indicators;
- Doctor summary;
- checksums/manifest.

Never include by default:
- credentials/tokens;
- capture files;
- private keys;
- precise location;
- raw sensitive network history.

This could dramatically improve community troubleshooting quality.

---

## 3. PwnLint / ConfigGuard

Validate config before a restart turns a typo into a broken device.

Checks:
- TOML syntax;
- unknown/misspelled keys where schema knowledge exists;
- value type/range;
- plugin enabled but config absent;
- configured path/device missing;
- plugin dependency missing;
- conflicting display owners/plugins;
- impossible display dimensions/rotation;
- whitelist normalization/case warnings;
- duplicate/conflicting network settings;
- unsafe or stale option names across image versions.

Features:
- dry-run only by default;
- line/key-specific explanation;
- backup before any optional fix;
- config diff;
- version-aware rules.

Potential WebUI action:
**CHECK CONFIG BEFORE RESTART**

---

## 4. RadioDoctor

Dedicated read-only radio/monitor health inspector.

Useful evidence:
- phy/interface inventory;
- managed + monitor coexistence;
- driver/firmware/Nexmon version;
- supported channels;
- regulatory restrictions;
- configured channel set;
- actual active/recent channels;
- monitor interface MAC/state;
- repeated monitor loss/recreation;
- bettercap interface selection;
- channel-hop progress/stalls;
- driver reset/re-enumeration signatures.

Goal:
answer **why is my Pwnagotchi scanning badly / stuck / blind?** without forcing
the user to manually collect ten shell commands.

This is intentionally diagnostic. It does not add new offensive behavior.

---

## 5. DisplayDoctor

A Pwnagotchi display/touch diagnostics plugin/helper.

This addresses a recurring practical gap: “white screen / wrong display type /
touch does not work” currently turns into manual device-tree and framebuffer
debugging.

Collect:
- /dev/fb*;
- /proc/fb;
- framebuffer geometry/depth;
- loaded overlays;
- SPI devices;
- device-tree compatible strings;
- display-related kernel modules;
- touch input devices;
- rotation;
- current Pwnagotchi display config;
- renderer/plugin ownership;
- known common panel fingerprints.

Functions:
- read-only report;
- safe test-pattern command;
- optional known-recipe suggestions;
- export support bundle.

No blind config rewriting.

---

## 6. StorageSentinel / SD Rescue

Watch for early evidence of storage trouble.

Signals:
- MMC timeout/I/O errors;
- ext4 errors;
- filesystem remounted read-only;
- low/critical free space;
- database write failures;
- repeated unexpected reboot indicators;
- package-manager corruption/half-configured state.

Response levels:
1. warn;
2. preserve small critical configuration/state to a healthy alternate destination;
3. recommend Rebuild Bundle;
4. recommend offline/full imaging only if appropriate.

Important:
do not automatically hammer a suspected failing SD with a complete raw read as
the first response.

---

# Priority B — strong utility

## 7. PluginDoctor / Dependency Inspector

Scan installed custom/default plugins and explain:
- enabled/disabled;
- source/path/version where inferable;
- import errors;
- missing Python modules;
- missing executables/services/files;
- expected config keys;
- credential presence without exposing values;
- display ownership/conflict;
- callback errors;
- optional README/docs link;
- restart behavior.

Longer-term:
- callback runtime/error profiler;
- dependency graph;
- “USED BY”;
- safe staged config template.

This directly addresses the common desire to install many plugins but keep them
understandable and toggleable.

---

## 8. PwnGuide / Contextual Help

Add small contextual help affordances to the WebUI.

For important options:
- What is this?
- What does changing it do?
- Does it need reboot/restart?
- Why is it unavailable?
- What does it depend on?
- Show relevant local documentation/runbook.

Desktop can use hover + click; touch uses tap.

Possible knowledge sources:
- Jayofelony docs;
- local plugin README;
- verified local runbooks;
- Linux/package documentation.

This can remain deterministic without AI.

---

## 9. ChangeJournal / Config Rollback

Track meaningful administrative changes:
- config.toml revisions;
- plugin enable/disable;
- important package/version changes;
- display changes;
- network/tether changes.

Store:
- timestamp;
- before/after hashes;
- bounded diff;
- backup reference;
- restart/reboot performed;
- result.

Goal:
**What changed since it worked?**

---

## 10. UpdatePreflight

Companion to auto-update, not a competing updater.

Before a risky update:
- power state;
- free space;
- filesystem writable/healthy;
- apt/dpkg consistency;
- Internet/DNS;
- required backup freshness;
- driver/kernel compatibility checks;
- service quiesce plan where appropriate.

After:
- package consistency;
- driver/module/service health;
- monitor interface;
- Pwnagotchi health.

If update prerequisites are bad, explain instead of beginning.

---

## 11. Exact Screen Mirror

Expose the actual current framebuffer/Pwnagotchi-rendered image in a diagnostic
WebUI page.

Possible extras:
- display dimensions;
- refresh age;
- optional touch coordinate overlay;
- current display owner/plugin;
- screenshot export.

Remote input should be a separate explicit feature, not silently enabled.

Useful for:
- theme creation;
- display support;
- remote troubleshooting;
- showing another person exactly what the physical panel receives.

---

## 12. Hardware Profile / Inventory Export

Create a concise hardware fingerprint:
- Pi model;
- display/touch;
- onboard/external radios;
- USB devices;
- Bluetooth;
- GPS;
- battery/UPS;
- storage;
- kernel/modules;
- relevant buses.

Use:
- support;
- plugin compatibility;
- reproducible bug reports;
- known-good hardware profiles.

---

# Priority C — useful experiments

## 13. Connectivity Matrix

A focused dashboard for:
- USB gadget;
- Bluetooth tether;
- Ethernet;
- Wi-Fi management link;
- default route;
- DNS;
- Internet reachability.

Show the distinction between:
- interface up;
- address assigned;
- route exists;
- DNS works;
- Internet works.

This may ultimately become a PwnDoctor view instead of a separate plugin.

---

## 14. Backup Auditor / Recovery Manifest

Jayofelony already ships `auto_backup`; do not clone it merely to have another
backup plugin.

The gap worth exploring is:
- what is actually protected?
- can it rebuild a blank replacement SD?
- when was backup last verified?
- are custom plugins/config/display files covered?
- package/version manifest;
- restore instructions;
- checksum verification.

A full bare-metal backup may be better as a helper/service outside the
Pwnagotchi process.

---

## 15. Plugin Profiler

Development tool that measures:
- callback runtime;
- repeated errors;
- exception count;
- memory/RSS change where measurable;
- slow WebUI endpoints;
- event frequency.

Goal:
find “this plugin makes my Pwnagotchi unstable/hot/slow.”

Must be designed carefully because wrapping plugin callbacks can itself be
intrusive.

---

## 16. Local Runbook Registry

Machine-readable local troubleshooting procedures.

Possible front matter:
- applies_to;
- symptoms;
- probes;
- interpretation;
- safe fixes;
- restart/reboot;
- rollback;
- source/provenance.

PwnDoctor/PwnGuide can use the same registry.

This is a useful standalone Pwnagotchi idea and a direct prototype of the Beast
Runbook architecture.

---

## 17. First-Boot / Post-Upgrade Self Test

A bounded health wizard:
- image/version;
- services;
- radio/monitor;
- display/touch;
- storage;
- networking;
- plugin load;
- config validity.

Produces:
**READY / NEEDS ATTENTION**

Could be especially useful after major Jayofelony image updates.

---

# Upstream issue signals that informed this backlog

Current Jayofelony issues reviewed during this pass included:
- #641 — USB gadget connectivity/self-assigned IP on macOS;
- #640 — Bluetooth tether route works while DNS is broken;
- #638/#639 — configurable USB gadget networking/conflict handling;
- #618 — brcmfmac/Nexmon instability, reboot/recovery and a DKMS update left
  half-configured;
- #633 — whitelist MAC case handling can silently fail.

These do not prove every proposed plugin is unique. They do demonstrate that
diagnostics, configuration validation, update safety and support evidence remain
valuable problem areas in the current ecosystem.

---

# Suggested first implementation order

1. **PwnDoctor**
2. **PwnSupport Bundle**
3. **PwnLint / ConfigGuard**
4. **RadioDoctor**
5. **DisplayDoctor**
6. **StorageSentinel**
7. **PluginDoctor**
8. **Exact Screen Mirror**

Why:
those eight create an unusually strong maintenance/support layer without
changing Pwnagotchi's core purpose or duplicating Bettercap.

They also generate reusable evidence/contracts that Beastagotchi can later
consume.

---

# Relationship to Beastagotchi

Keep the projects separate but interoperable.

Where useful, a Pwnagotchi experiment should expose clean data rather than
hard-coding Beast behavior.

Possible future adapters:
- PwnDoctor findings → Beast Doctor;
- PwnSupport Bundle → Beast Support evidence;
- RadioDoctor → Beast radio Signals;
- DisplayDoctor → Beast Hardware/Presentation Studio;
- PluginDoctor → Beast Plugin & Capability Center;
- Screen Mirror → Beast Exact Remote Mirror;
- Runbooks → Beast Runbook Registry.

The Pwnagotchi plugin remains useful even for someone who never installs
Beastagotchi.
