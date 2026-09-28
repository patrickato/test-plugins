# Notes: backup plugin cluster

**Status: `auto_backup_ng.py` REMOVED (strictly-inferior duplicate).
`AutoBackup v2.0` and `GitHub_Backups` KEPT.**

Sources: `auto_backup_ng.py` from `itsdarklikehell/pwnagotchi-plugins`
(compared by diff against its unmodified original, dadav's
`auto_backup.py`, found in
`pwnagotchi-unofficial/plugins_archive/dadav/pwnagotchi-custom-plugins`).
`AutoBackup v2.0` and `GitHub_Backups` both from `wpa-2/Pwnagotchi-Plugins`
(`auto_backup.py` and `GitHub_Backups/git_backup.py`, class `git_backup`
- newly cloned for this cluster at `/home/claude/wpa-2/pwnagotchi-plugins`,
already present locally from Cluster 9's wardriving research).

## 1. What each one is and does

1. **`auto_backup_ng.py`** - on `on_internet_available`, runs a single
   shell command (default `tar czf /root/pwnagotchi-backup.tar.gz
   {files}`) against a fixed file list (brain files, handshakes,
   `/etc/pwnagotchi/`, the log). A `StatusFile` skips re-backing-up
   until `interval` days have passed. Always overwrites the same
   `.tar.gz` filename - no versioning, nothing to retain.
2. **`AutoBackup v2.0`** (file's own `__version__` is actually `"2.4"`)
   - timestamped local archives
   (`hostname-backup-YYYYMMDD-HHMMSS.tar.gz`), a configurable
   retention count (`max_backups_to_keep`, default 3) with automatic
   pruning, `include`/`exclude` path lists, a real background
   scheduler thread (minute-granularity, independent of the
   internet-available hook), disk-full self-healing (prunes before
   attempting a new backup and again on startup), and a webhook page
   with a manual "Backup Now" button.
3. **`GitHub_Backups`** (class `git_backup`) - mirrors files into a
   local git repo and force-pushes it to a GitHub/Gitea remote over
   SSH, regenerating a `restore.sh` and `README.md` inside the repo
   each run. Shows a small "last backup" UI element and has a styled
   webhook page for manual triggers.

## 2. `auto_backup_ng.py` - removed, confirmed non-functional-as-described

Diffed line-for-line against dadav's unmodified original. The only
differences: class name (`AutoBackup_ng` vs `AutoBackup`), an added
but empty/misleading `__GitHub__ = ""` attribute, f-strings replacing
`%`-style formatting, log tags switched from `[autobackup]` to
`[{self.__class__.__name__}]`, and two added no-op hooks
(`on_unload` that only logs, `on_webhook` that only logs and returns
`None`).

**The master list's prior description ("with retention/garbage
collection") does not match the code** - there is no retention or
pruning logic anywhere in this file. It always writes to the exact
same fixed filename (`/root/pwnagotchi-backup.tar.gz`), so each run
simply overwrites the previous backup. This looks like a
documentation inaccuracy inherited from an earlier pass, not a
plugin bug - corrected here rather than carried forward.

**Secondary gap:** the added `on_webhook(self, path, request)` logs a
line and has no `return` statement, so it implicitly returns `None`.
Pwnagotchi's webhook handling is Flask-based and expects a response
object/string back from view functions - visiting this plugin's
webhook page would likely error rather than show anything. Not
fixed, since the plugin was removed rather than kept.

**Why removed instead of fixed:** `AutoBackup v2.0` already does the
exact same job (local tar-based backup of config/SSH keys/handshakes)
with retention, pruning, disk self-healing, and a background thread -
running both would just be two overlapping local-backup jobs writing
to different files for no added benefit. Removed as a
strictly-inferior duplicate, same reasoning class as the
`apfaker.py`/`better_apfaker.py` removal in Cluster 14.

## 3. `AutoBackup v2.0` - kept, no bugs found

The most carefully engineered plugin in this cluster. Its own code
comments reference a previously-fixed real bug ("issue #617") where
the backup directory could end up archiving itself recursively and
fill the disk - the fix (`_enforce_backup_location_exclude`, which
force-adds the backup directory to the exclude list regardless of
user config) is present and applied unconditionally. Also handles a
legacy config-format migration gracefully (detects an old
single-string `commands` format and substitutes the correct default
rather than crashing on it). Uses the same config-driven path
resolution helper (`_config_value`/`config_handshake_dir`/
`config_custom_plugins_dir`) as `GitHub_Backups` - reads
`bettercap.handshakes` and `main.custom_plugins` from the live
config with sensible canonical-path fallbacks, so it adapts to
wherever this fork's config actually points rather than hardcoding
paths written for a different fork.

**Naming note:** the master list calls this "v2.0," but the file's
own `__version__` field says `"2.4"` - cosmetic mismatch only, no
functional issue. Worth updating the master-list bullet text
whenever this project does a broader description-accuracy pass.

## 4. `GitHub_Backups` - kept, one architecture note

Solid, complete implementation: SSH-key validation on load, a
cooldown gate (`interval` hours, default 2) via a small JSON status
file, path-mirroring copy logic with mtime/size-based skip-if-
unchanged, generated `restore.sh` and `README.md` written into the
backup repo every run, and a styled webhook page with a live status
card and manual trigger. Correctly avoids the recurring
`__defaults__`-declaration bug found elsewhere in this project by
using `self.options.get(key, default)` throughout instead of relying
on a class-level `__defaults__` dict - `on_loaded()` also validates
`github_repo` and the SSH key path up front and bails out cleanly
(`self.ready = False`) rather than crashing later if either is
missing.

**Architecture note:** `on_internet_available` calls
`self._perform_backup()` directly - synchronously, not in a spawned
thread. `_perform_backup()` does file copying plus three git
operations (`init`/`add`/`commit`/`push --force` over SSH), which is
a finite but potentially slow operation, especially the network
push. `AutoBackup v2.0` spawns its equivalent work in a background
`Thread`; this plugin does not, so a slow or stalled SSH connection
to the remote could block whatever hook-processing this fork does
while the push is in flight (caveat: based on how `on_internet_available`
and similar hooks are used across every other plugin reviewed in
this project, not on having read the core agent-loop source directly
in this session). Same underlying concern class as `better_apfaker.py`'s
finding in Cluster 14, but meaningfully less severe there - this is
a bounded, one-shot network call gated by a multi-hour cooldown, not
an unbounded `while` loop that runs for as long as the plugin is
active.

**Fix, if ever prioritized:** wrap the `self._perform_backup()` call
in `on_internet_available` in a background `threading.Thread`, same
pattern `AutoBackup v2.0` already uses for its own scheduler/backup
work. Not applied, documented for whenever this plugin is actually
enabled and the SSH push proves slow in practice.

**Design choice, not a bug:** `git push --force` every run is
intentional (one-way backup, documented in the repo's own generated
README) - no push history is retained on the remote, only the latest
snapshot. Version string is also slightly inconsistent internally
(`__version__ = "2.2"` in the class vs. "v2.1.0.1" printed in the
webhook page footer) - cosmetic only.

## 5. Dependencies (kept plugins)

`AutoBackup v2.0`: `tar` (apt, standard), `toml` (pip, already a core
pwnagotchi dependency). No additional hardware.
`GitHub_Backups`: `git` (apt, standard), a passwordless SSH key
(`ssh-keygen -t ed25519`) with its public half added as a deploy key
(or account key) on the target GitHub/Gitea repo, and outbound SSH
(port 22) reachability to the git host - the only plugin in this
cluster with an actual network/account setup requirement beyond what
pwnagotchi ships with.
