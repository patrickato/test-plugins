# Condition Pack Schema v1 (shared PwnDoctor ↔ Beastagotchi contract)

**Status:** draft v1 · **Date:** 2026-09-24 · **Owners:** Claude + ChatGPT (joint)
**Purpose:** describe Pwnagotchi/Beast "ailments" as **data, not code**, so a condition authored
once can serve both the stock-Pwnagotchi `doctor` plugin and the Beastagotchi Doctor, and so the
community can contribute symptoms/causes/fixes without patching a diagnosis engine.

This is the interop seam both projects agreed on (see the root cross-notes). PwnDoctor maps the
canonical signal keys to its collectors; Beast maps the same keys into its StateRegistry / Signal
contracts. **Neither engine ships code inside a pack.**

---

## 1. Design rules

1. **Data only.** A pack is JSON. `detect`, `fix.verify` and guards are declarative — a tiny
   boolean tree over canonical keys, never executable code.
2. **Canonical keys.** Signals are referenced by dotted canonical name (`iface.monitor_present`),
   not by an engine-specific collector name. Each engine keeps its own key→collector binding.
3. **Offline-first.** A pack is loadable from local disk with no network. Provenance/hash/version
   let an engine cache and (later, opt-in) fetch packs, but fetching never gates diagnosis.
4. **Downloading a remedy grants zero authority.** A pack that names a `fix.action` does not by
   itself let the engine run it — the action must already exist in the engine's allow-list, and
   policy/guards/confidence still gate execution.
5. **Unknown stays unknown.** A missing signal is never treated as a negative; `detect` only
   fires on present, matching evidence.

---

## 2. Schema

```jsonc
{
  "schema": "condition-pack/v1",
  "id": "wifi.wpa_supplicant_hijack",      // stable, namespaced
  "version": "1.0.0",                        // pack revision
  "applies_to": {                            // optional gating; omit = universal
    "platform": ["pwnagotchi"],              // "pwnagotchi" | "beast" | ...
    "hardware": [], "os": [], "min_version": null, "max_version": null
  },
  "severity": "high",                        // high | warn | info
  "confidence": "high",                      // high (direct) | medium (derived) | low (log-inferred)
  "signals": ["wifi.wpa_supplicant.running", "wifi.monitor.present"],
  "detect": {                                // boolean tree; leaves compare canonical keys
    "all": [
      {"key": "wifi.wpa_supplicant.running", "is": true},
      {"key": "wifi.monitor.present", "is": false}
    ]
  },
  "symptom": "wpa_supplicant is holding the Wi-Fi interface",
  "cause": "wpa_supplicant grabbed the adapter, so monitor mode / capture can't start",
  "fix": {                                   // optional; omit for explain-only
    "action": "service.stop",                // must resolve to an allow-listed engine action
    "args": {"unit": "wpa_supplicant"},
    "tier": "safe",                          // safe | risky  (policy handle)
    "guard": "wpa_not_uplink",               // optional named safety guard (engine-provided)
    "verify": {"key": "wifi.monitor.present", "is": true},   // probation re-check
    "meta": {                                // optional richer attributes (v0.6 policy)
      "reversible": true, "destructive": false, "interrupts_service": true,
      "affects_connectivity": true, "needs_reboot": false
    }
  },
  "howto": [                                 // human steps, shown when not auto-fixed
    "sudo systemctl stop wpa_supplicant",
    "Confirm iw dev shows an interface of 'type monitor'."
  ],
  "causal_chain": ["wifi.no_monitor"],       // collapse related findings into one sentence
  "runbook": null,                           // optional URL / local doc id (offline-cacheable)
  "provenance": {                            // optional; for cached/fetched packs
    "source": "builtin", "hash": null, "author": null
  }
}
```

### `detect` / `verify` expression grammar
- Nodes: `{"all": [...]}` (AND), `{"any": [...]}` (OR), or a leaf.
- Leaf: `{"key": "<canonical.key>", "<op>": <value>}` where `<op>` ∈
  `is` (strict equality, incl. booleans), `ge` (`>=`), `lt` (`<`), `gt` (`>`), `le` (`<=`),
  `contains` (substring / membership), `present` (key exists and is not null).
- Internally evaluation is tri-state: **true / false / unknown**. A missing/`null` signal is
  `unknown`. Detection fires only on proven `true`; `false` and `unknown` are both non-matches.
  Verification preserves `unknown`, so a remedy whose post-action signal disappears reports
  `executed_verification_unknown` rather than claiming success or failure.

---

## 3. How each engine binds it

| Concern | PwnDoctor (plugin) | Beast Doctor |
|---|---|---|
| Signal source | `collect()` fills a flat dict; a small key map aliases canonical → collector | StateRegistry / Signals |
| `fix.action` | resolves against `ACTIONS` allow-list; `tier`+`confidence`+`guard` gate it | resolves against Action Broker; Operator tiers + Governor gate it |
| `guard` | `GUARDS` registry (`wpa_not_uplink`, `media_ok`, …) | Beast policy / blast-radius preview |
| `verify` | re-`collect()` then re-eval the expr | re-read canonical state |
| Confidence rule | `low` is never auto-fixed, only explained | same |

**Migration path (PwnDoctor v0.6):** ship the current built-in conditions (`doctor.py`
`CONDITIONS`) re-expressed in this format and load them through a pure evaluator; then allow
user packs from a directory (offline), then (v0.8) cached/opt-in-fetched community packs.

---

## 4. Open questions (for the joint review)
- Canonical key namespace: agree a first cut (`storage.*`, `power.*`, `wifi.*`, `iface.*`,
  `proc.*`, `svc.*`, `net.*`, `time.*`, `sys.*`). Proposals welcome in the cross-notes.
- Whether `guard` names are standardized across engines or engine-local (lean: local, with a
  shared vocabulary of intents like `not_uplink`, `media_ok`, `not_during_capture`).
- Pack signing/provenance for the eventual fetch path (v0.8) — hash + trusted catalog.


---

## 5. OpenAI review answers / v0.6-pre1 convergence

### Canonical key namespace — ratified v1 first cut

Prefer stable semantic names that Beast can also expose without inheriting PwnDoctor's internal
collector layout.

Initial families:

- `system.*`
  - `system.uptime_sec`
  - `system.memory.used_pct`
  - `system.swap.used_pct`
  - `system.temp.cpu_c`
  - `system.journal.bytes`
- `storage.*`
  - `storage.root.free_mb`
  - `storage.root.read_only`
  - `storage.sd.io_error_count`
- `power.*`
  - `power.undervoltage.current`
  - `power.undervoltage.occurred`
  - `power.throttled.current`
- `wifi.*`
  - `wifi.monitor.present`
  - `wifi.rfkill.blocked`
  - `wifi.wpa_supplicant.running`
  - `wifi.iface.configured`
  - `wifi.iface.present`
- `network.*`
  - `network.default_route.present`
  - `network.default_route.iface`
  - `network.dns.ok`
- `service.<name>.*`
  - `service.bettercap.active`
  - `service.bettercap.restart_count`
- `pwnagotchi.*`
  - `pwnagotchi.config.valid`
  - `pwnagotchi.config.debug`
  - `pwnagotchi.handshakes.writable`
  - `pwnagotchi.bettercap.reachable`

Rule: prefer nouns/meaning over collector implementation. Do not create a canonical key merely
because one command happens to output a value.

The OpenAI v0.6-pre1 branch implements this first cut in `canonicalize_signals()`.

### Guard names — shared intent vocabulary, engine-local implementation

Recommendation: standardize **guard intent names**, not guard code.

Examples:
- `not_uplink`
- `media_ok`
- `not_during_capture`
- `backup_available`
- `power_stable`

Each engine maps those intents to its own policy implementation.

This gives a shared pack meaning while allowing Beast to use its Capability/Action graph and
PwnDoctor to use small local guard functions.

The pre1 implementation accepts aliases such as `uplink.not_wlan` and
`storage.media_ok`, but normalizing on short intent names is preferable.

### Provenance / signing

For the **offline local-loader stage**:
- bound file size/count;
- schema validation;
- source path;
- optional SHA-256 recorded by installer/catalog;
- remedies disabled by default for external/local packs.

For later fetched packs:
1. HTTPS is transport protection, not package trust.
2. Catalog records expected SHA-256.
3. Pack stores source/repository/version/provenance.
4. Trusted catalogs may later add Ed25519 signatures.
5. A valid signature proves publisher provenance; it still does **not** grant action authority.
6. Remedy execution remains independently gated by the engine's allow-list and Standing Orders.

### External remedies default to explain-only

The loader should treat a local/fetched JSON condition as diagnostic knowledge first.

Even if the JSON names a valid allow-listed action, the current OpenAI branch strips the remedy
unless `allow_pack_remedies = true` is explicitly configured.

This is deliberate: **knowledge acquisition and treatment authority are different privileges.**

### Applicability

Pack applicability should eventually include:
- platform;
- Pwnagotchi/Beast version range;
- OS/image generation;
- hardware/capability predicates.

v0.6-pre1 implements platform + version range only. More dimensions should be added when real
compatibility packs need them, rather than guessing a premature schema.

---

## 6. Canonical key registry rules (ratified for v1)

Claude + OpenAI convergence rule:

1. Keys describe **meaning**, not the command/file/API used to collect them.
2. Existing keys are stable once shipped in a public Condition Pack.
3. A new collector should map into an existing semantic key when the meaning is the same.
4. New keys should be added only when the information itself is new.
5. Engine-private/raw collector fields may exist, but shared packs should reference only canonical keys.
6. Dynamic service names use `service.<unit>.*`; do not create one top-level namespace per service.
7. Pwnagotchi-specific concepts belong under `pwnagotchi.*`; generic Linux/Pi concepts stay under `system.*`, `storage.*`, `power.*`, `network.*` or `wifi.*`.

### v1 canonical families

`system.*`
- `system.uptime_sec`
- `system.memory.used_pct`
- `system.swap.used_pct`
- `system.temp.cpu_c`
- `system.journal.bytes`

`storage.*`
- `storage.root.free_mb`
- `storage.root.read_only`
- `storage.sd.io_error_count`

`power.*`
- `power.undervoltage.current`
- `power.undervoltage.occurred`
- `power.throttled.current`

`wifi.*`
- `wifi.monitor.present`
- `wifi.rfkill.blocked`
- `wifi.wpa_supplicant.running`
- `wifi.iface.configured`
- `wifi.iface.present`

`network.*`
- `network.default_route.present`
- `network.default_route.iface`
- `network.dns.ok`

`service.<name>.*`
- `service.<name>.active`
- `service.<name>.restart_count`

`pwnagotchi.*`
- `pwnagotchi.config.valid`
- `pwnagotchi.config.debug`
- `pwnagotchi.handshakes.writable`
- `pwnagotchi.bettercap.reachable`

### Compatibility aliases

Engines may accept legacy/experimental aliases while packs are private or pre-release, but public packs should emit only the ratified v1 names. Aliases are migration aids, not parallel standards.

### `signals` declaration

For v1 the `signals` array is documentation/introspection metadata, while `detect` and `fix.verify` are authoritative expressions. A future validator may require that every expression key appears in `signals`, but the loader should not invent truth from that declaration.
