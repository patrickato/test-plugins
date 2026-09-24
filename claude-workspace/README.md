# claude-workspace/

This folder is **Claude's own separate section** of this repository.

## Rules

- Claude (the AI assistant working with the repo owner) writes **only** inside `claude-workspace/`.
- Claude does **not** create, change, move or delete anything outside this folder unless the owner explicitly asks for that specific change.
- Claude's work lands on `claude/...` branches, never directly on `main`.
- Everything in here is a **proposal**. The owner, or another reviewing AI, looks at it before any of it is promoted into the main project.
- Moving something out of this folder into the real project is a separate, explicit step, done by the owner or at the owner's request.

## Layout

| Path | Purpose |
|---|---|
| `README.md` | These rules. |
| `reviews/` | Dated reviews and analysis documents meant for the owner and other AI reviewers. |
| `plugins/` | Plugin drafts and prototypes, created when plugin work starts. |

## Related

The long-running progress memory for this work lives in the Beastagotchi repository:

`patrickato/Beastagotchi`, branch `claude/workspace`, file `claude-workspace/BEASTAGOTCHI_PROGRESS.md`
