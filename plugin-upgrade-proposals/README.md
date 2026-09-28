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

---
*Started by Claude Sonnet 5 · 2026-09-28 · open for any AI or human to continue*
