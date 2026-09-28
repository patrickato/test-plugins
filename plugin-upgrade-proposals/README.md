# Plugin Upgrade Proposals

This folder is separate from `pwnagotchi-plugins/` on purpose. Nothing
here is installed, functional, or approved for build yet - these are
planning documents only: scope, design notes, and a proposed
`config.toml` for a plugin upgrade that's been discussed but not
greenlit.

**Nothing in `pwnagotchi-plugins/`, `release/`, or any existing file in
this repo gets edited, overwritten, or deleted by anything placed
here.** This folder only ever grows by addition - new cluster folders,
new proposal folders inside them. If a proposal is later approved and
built, the resulting plugin goes into `pwnagotchi-plugins/<name>/` as
its own new folder, same as every other plugin in this repo - it does
not retroactively rewrite anything in this planning folder either.
Old proposals stay as a record even after being built or abandoned,
until a manual cleanup pass decides otherwise.

This is meant to be a workspace any AI assistant (or human) can pick
up and continue - not just a single-session scratch space. Each
proposal document is written to stand alone: enough context to pick
up cold, no dependency on remembering a prior conversation.

## Structure

```
plugin-upgrade-proposals/
  README.md                          <- this file
  cluster-NN-<short-name>/            <- one folder per elimination-list duplicate cluster
    <plugin>-upgrade/
      PLAN.md                         <- scope, design, rationale
      config-example.toml             <- proposed config, not yet wired to real code
```

## Status key (used inside each PLAN.md)

| Status | Meaning |
|---|---|
| `PROPOSED` | Scope/design written, not approved to build |
| `APPROVED` | User signed off, not yet built |
| `BUILT` | Code exists - see `pwnagotchi-plugins/<name>/` for the real plugin |
| `ABANDONED` | Decided against, kept for the record |

## Index

### Cluster 2 - aggressive/instant-attack mode

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 14 (all three
kept on the master list; these are upgrade proposals discussed
alongside that decision, not replacements pulled from the list).

| Proposal | Target plugin | Status |
|---|---|---|
| [`hulk-upgrade`](cluster-02-aggressive-attack-mode/hulk-upgrade/PLAN.md) | `hulk.py` | PROPOSED |
| [`instattack-upgrade`](cluster-02-aggressive-attack-mode/instattack-upgrade/PLAN.md) | `instattack.py` | PROPOSED |
| [`probenpwn-upgrade`](cluster-02-aggressive-attack-mode/probenpwn-upgrade/PLAN.md) | `probenpwn.py` | PROPOSED |

### Cluster 3 - auto-authenticate + recon on known networks

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Groups 15-16. A
verification pass on this cluster found `educational-purposes-only.py`
and `woop_woop.py` both fail to load on this image outright (dead
top-level import of a module removed from this fork's AI/RL layer);
`hp_educational-purposes.py` was removed from the master list entirely
(functionally inert on both its claimed features, needs a rebuild not
a tweak); `educational-purposes-exclusively.py` already works. See
Group 15/16 in the master list's elimination log for full findings on
all four plugins in this cluster.

| Proposal | Target plugin | Status |
|---|---|---|
| [`educational-purposes-only-upgrade`](cluster-03-auto-authenticate-recon/educational-purposes-only-upgrade/PLAN.md) | `educational-purposes-only.py` | PROPOSED |
| [`woop-woop-upgrade`](cluster-03-auto-authenticate-recon/woop-woop-upgrade/PLAN.md) | `woop_woop.py` | PROPOSED |
| [`educational-purposes-exclusively-notes`](cluster-03-auto-authenticate-recon/educational-purposes-exclusively-notes/NOTES.md) | `educational-purposes-exclusively.py` | KEPT AS-IS - notes only |
| [`hp_educational-purposes-removed`](cluster-03-auto-authenticate-recon/hp_educational-purposes-removed/NOTES.md) | `hp_educational-purposes.py` | REMOVED - record only |

### Cluster 5 - pcap→hash conversion

Source: `pwnagotchi-plugins/MASTER_PLUGIN_LIST.md`, Group 18. A fourth
plugin (`hashie_ng.py`, co-authored by jayofelony himself) was found
during this cluster's review and added to the master list. All three
plugins in this cluster share one bug (documented once, applies to
all): their live conversion path works fine, but their startup
backlog-scan filters for `.pcap` only and never matches this image's
`.pcapng` files.

| Proposal | Target plugin(s) | Status |
|---|---|---|
| [`shared batch-scan pcapng fix`](cluster-05-pcap-hash-conversion/NOTES.md) | `hashie-hcxpcapngtool.py`, `hashieclean.py`, `hashie_ng.py` | KEPT AS-IS - documented fix, low priority |

---
*Started by Claude Sonnet 5 · 2026-09-28 · open for any AI or human to continue*
