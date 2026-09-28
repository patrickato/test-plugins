# best_quickdic

Runs a dictionary crack attempt against every captured handshake,
without blocking the pwnagotchi main loop and without the specific
bugs found in the community plugins it replaces.

Self-contained folder, separate from the other plugins in this repo.

## Files in this folder

| File | Purpose |
|---|---|
| `best_quickdic.py` | The plugin itself. Goes on the Pi. |
| `config-example.toml` | The config block to copy into pwnagotchi's `config.toml`. |
| `README.md` | This file. |

## What this replaces, and why

This plugin was written to replace three community plugins that all
do the same basic job - quick on-device dictionary cracking of a
captured handshake - after a line-by-line review of their actual
source code turned up concrete, specific defects:

**`quickdic.py`** and **`better_quickdic.py`** (the latter is
essentially a renamed copy of the former, with a QR-code extra bolted
on) both shell out to `aircrack-ng` **synchronously, inline, inside
`on_handshake`**, with no timeout on the subprocess call. That means
the entire pwnagotchi main loop - UI updates, epoch handling, grid
communication, everything - stalls for as long as the crack attempt
runs. Against a large wordlist, that can be minutes with the device
completely unresponsive. Neither plugin has any way to bound that.

**`pwnagotchi_fast_dictionary`** is architecturally better - it
verifies the handshake at the packet level with `scapy` instead of
text-grepping `aircrack-ng`'s output, and it added a per-wordlist
timeout so a single slow wordlist can't hang forever. But its
wordlist-discovery code has a live bug:

```python
list_of_wordlists = os.listdir()   # <- no argument
```

`os.listdir()` called with no argument lists the **current working
directory**, not the configured `wordlist_folder`. Unless the
process's cwd happens to equal the wordlist folder (it won't, in
normal use), this plugin silently fails to find the user's actual
wordlists and has nothing to crack against.

All three also hand the raw capture filename straight to
`aircrack-ng` (and, in `fast_dictionary`'s case, to `scapy.rdpcap()`
as well) with no format conversion step, so their compatibility with
a `.pcapng`-only capture format depends entirely on whatever pcap
parsing happens to be built into the installed `aircrack-ng` binary.

`best_quickdic` fixes all of the above:

1. **Runs off the main thread.** Every crack attempt spins up on a
   `threading.Thread`, so the agent keeps running normally no matter
   how long a wordlist pass takes.
2. **Converts through `hcxpcapngtool` first**, which is written for
   this exact capture format. A successful, non-empty `.hc22000`
   output is itself proof a crackable handshake/PMKID was present -
   no separate text-grep or packet-layer check needed.
3. **Globs the configured folder correctly** -
   `glob.glob(os.path.join(wordlist_folder, '*.txt'))` - so it can't
   silently end up pointed at the wrong directory the way
   `fast_dictionary` does.
4. **Enforces a real, double-backstopped timeout** - hashcat's own
   `--runtime` flag, plus a `subprocess.run(timeout=...)` on top of
   that in case hashcat itself doesn't respect it - and moves on to
   the next wordlist rather than ever hanging.
5. **Cracks with `hashcat -m 22000`** against the converted file,
   rather than re-running `aircrack-ng` directly against the raw
   capture.

## How it works

1. On every new handshake capture, checks it hasn't already been
   processed (dedup by filename).
2. Kicks off a background thread so the main loop is never blocked.
3. Converts the capture to `.hc22000` via `hcxpcapngtool`. If that
   produces nothing, logs it and stops - there was no crackable
   handshake/PMKID in the file.
4. Globs every `*.txt` file in `wordlist_folder`, alphabetically.
5. Runs `hashcat -m 22000` against the converted hash, one wordlist
   at a time, with a hard per-wordlist timeout. Stops and logs the
   result as soon as one wordlist cracks it.
6. If every wordlist is exhausted with no result, logs that too.

## Requirements

```bash
sudo apt install hcxtools hashcat
```

- **hcxtools** - provides `hcxpcapngtool`, used for the `.pcapng` →
  `.hc22000` conversion step.
- **hashcat** - does the actual cracking. The Raspberry Pi 4's CPU
  runs hashcat's CPU backend only (no GPU) - fine for small/medium
  wordlists, slow for anything the size of `rockyou.txt` or larger.
  The `per_wordlist_timeout_secs` setting exists specifically to
  bound how long you let that run before giving up and moving on.
- **Python** - no extra Python packages needed beyond the standard
  library; the plugin only uses `os`, `glob`, `time`, `logging`,
  `subprocess`, `threading`, and `datetime`, all already available in
  a standard pwnagotchi Python environment.
- **At least one `.txt` wordlist** placed in the configured
  `wordlist_folder`. None is bundled - you supply your own. One word
  per line, standard format (the same format `aircrack-ng`/`hashcat`
  both expect).

## Install

1. Copy the plugin to the Pi:
   ```powershell
   scp best_quickdic.py pi@pwnagotchi.local:/tmp/
   ```
   ```bash
   sudo mv /tmp/best_quickdic.py /usr/local/share/pwnagotchi/custom-plugins/
   ```
2. Add the config block from `config-example.toml`, adjusting
   `wordlist_folder` to point at wherever your `.txt` wordlists
   actually live on the Pi.
3. Restart:
   ```bash
   sudo systemctl restart pwnagotchi
   ```
4. Confirm it loaded:
   ```bash
   sudo journalctl -u pwnagotchi -b | grep best_quickdic
   ```

## Config quick reference

| Key | Default | Meaning |
|---|---|---|
| `enabled` | — | Must be `true` to activate |
| `wordlist_folder` | `/home/pi/wordlists` | Folder globbed for `*.txt` wordlists |
| `export_dir` | `/home/pi/best_quickdic/exports` | Where `.hc22000` files land |
| `log_file` | `/home/pi/best_quickdic/results.log` | Plain-text run log |
| `per_wordlist_timeout_secs` | `300` | Hard timeout per wordlist attempt |
| `convert_timeout_secs` | `60` | Timeout for the hcxpcapngtool conversion step |
| `max_wordlists_per_handshake` | `0` (no limit) | Optional cap on wordlists tried per handshake |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "required tool(s) not found" at load | `hcxtools` and/or `hashcat` not installed - `sudo apt install hcxtools hashcat` |
| "no crackable handshake/PMKID found" every time | Capture genuinely has no full handshake/PMKID, or `hcxpcapngtool` isn't installed correctly - test manually: `hcxpcapngtool -o test.hc22000 <a captured .pcapng file>` |
| "converted OK but no .txt wordlists found" | `wordlist_folder` is empty, doesn't exist, or files don't end in `.txt` |
| Every wordlist times out with no result | Wordlist too large for the timeout given Pi 4's CPU-only hashcat speed - raise `per_wordlist_timeout_secs`, use a smaller/more targeted wordlist, or crack offline on faster hardware instead |
| Main loop still feels sluggish during a crack | Check you're on this plugin and not still running `quickdic.py`/`better_quickdic.py`/`pwnagotchi_fast_dictionary` alongside it - those block the loop; `best_quickdic` shouldn't |

## Uninstall

```bash
sudo rm /usr/local/share/pwnagotchi/custom-plugins/best_quickdic.py
```
Remove the `main.plugins.best_quickdic.*` block from `config.toml` and
restart.

## Scope note

Not SSID-scoped, and deliberately so - this plugin never transmits
anything or targets a network. It only ever reads a handshake file
that's already been captured and sitting on disk, converts it, and
runs an offline dictionary attack against the converted hash locally.
That's pure post-processing of data already on the device, not active
behavior against any network, so it doesn't carry a `targets` list
the way an active attack/assoc/deauth plugin would.

---
*Author: patrickato · Added via Claude · version 1.0.0*
