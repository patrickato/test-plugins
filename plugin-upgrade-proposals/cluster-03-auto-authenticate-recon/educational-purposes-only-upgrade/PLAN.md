# Upgrade proposal: `educational-purposes-only.py` → `educational_purposes_only_plus` (working name)

**Status: PROPOSED — not approved, not built.**

## What this replaces and why

`educational-purposes-only.py` (itsdarklikehell/pwnagotchi-plugins,
credited to `@nagy_craig`/c-nagy's original) auto-connects to a single
operator-configured home network and, per its docstring, performs
internal network recon. Direct source review (pulled from the real
repo, not a description) found:

- **It cannot load on this image at all, as shipped.** Line 14 is a
  top-level `from pwnagotchi.ai.reward import RewardFunction` import.
  That module was fully removed from jayofelony's fork along with the
  rest of the AI/RL layer. The import is never even used anywhere
  else in the file - it's dead code that happens to sit at module
  scope, which is enough to make the whole plugin fail to import.
  **This is the single blocking issue and the first fix, full stop.**
- **Scoping is real and correct once that's fixed.** `on_wifi_update`
  only acts when `network['hostname'] == self.options['home-network']`
  and only above a configured RSSI floor - a single operator-named
  SSID, your own password from config, no guessing/cracking. This
  part doesn't need to change.
- **The "recon" claim doesn't match the code.** Despite the docstring
  and an nmap apt dependency listed in the README, no nmap call, ARP
  sweep, or port scan exists anywhere in the file. The only
  post-connection action is `dhclient wlan0` - get an IP, stop.
- **`on_epoch` looks broken.** It calls
  `subprocess.Popen("iwconfig wlan0").read()` - a bare `Popen` object
  has no `.read()` method without `stdout=subprocess.PIPE`; this would
  raise `AttributeError` if that code path is ever actually hit.
  `on_wifi_update` uses `os.popen(...).read()` correctly instead -
  inconsistent, and the `on_epoch` path looks untested.
- **A stray closing parenthesis** in the `hostnamectl set-hostname`
  shell command is a likely silent syntax error.
- **Every `subprocess.Popen()` call is fire-and-forget** - no
  `.wait()`, no return-code check, stdout redirected to `/dev/null`.
  If `macchanger` isn't installed, or any step in the long
  disable-driver / randomize-MAC / reconnect chain fails, the plugin
  has no way to know and just keeps going on a fixed `time.sleep()`
  schedule regardless.
- **Deliberate stealth behavior worth a config option, not a default.**
  MAC randomization (`macchanger -A`) and a randomized DHCP hostname
  pulled from `/usr/share/dict/words` are unconditional. The code
  comment says this is "for added stealth since their DHCP server
  will see this name" - on your own router, that's just obfuscating
  your own device from your own logs, which makes debugging harder
  for no real benefit. Should be an opt-in, not baked in.
- **Global mutable module state** (`READY`, `STATUS`, `NETWORK`)
  instead of instance attributes.

## Proposed scope

**Priority 0 (blocking - nothing else matters until this is done):**
1. Delete the `from pwnagotchi.ai.reward import RewardFunction` line
   entirely. It's unused dead code causing a hard load failure. This
   alone would make the plugin loadable again on this image.

**In scope after that:**
2. Fix `on_epoch`'s broken `Popen(...).read()` call - either switch to
   `subprocess.run(..., capture_output=True, text=True).stdout` or
   match `on_wifi_update`'s working `os.popen(...).read()` pattern.
3. Fix the stray-parenthesis hostname bug.
4. Check return codes / actually wait on the critical subprocess
   calls (driver reload, MAC randomization, wpa_supplicant start) so
   a failure is logged instead of silently ignored and slept through
   anyway.
5. Replace the long chain of fixed `time.sleep(10)` calls with actual
   state checks where feasible (e.g. poll `wpa_cli status` for
   `wpa_state=COMPLETED` instead of blindly sleeping 10s and hoping) -
   faster on a good connection, more honest on a bad one.
6. **Make MAC randomization and hostname spoofing configurable,
   default off** for connections to your own declared home network -
   there's no adversary to hide from on your own LAN. Keep the
   capability available (useful if this ever got reused for a
   different scoped target), just not forced on.
7. **Either implement the recon step for real, or drop the claim.**
   If real internal recon is wanted: a scoped, config-gated
   `nmap`/scapy ARP sweep of the local subnet only, after a
   successful connection to the one configured home network - never
   against anything else, since this plugin never connects anywhere
   else. If not wanted: rewrite the description/docstring so it
   doesn't promise something the code doesn't do. This is a real
   decision point, not a default - see open questions below.
8. Move `READY`/`STATUS`/`NETWORK` from module globals to instance
   attributes.

**Explicitly out of scope:**
- Any change to the RSSI/config-based single-SSID scoping model - it
  already works correctly and shouldn't be touched.
- Any credential-guessing/cracking logic - the original never had
  any, and none should be added.

## Open design questions (for discussion before build)

- Do you actually want the recon step implemented, or is "connect to
  my own network and get online" the whole job you want this plugin
  doing? Given you already have dedicated tooling elsewhere for
  active/scoped network work, a case can be made for just fixing the
  load-breaking bug and the real code-quality issues, and leaving
  "recon" out rather than building a new LAN-scanning feature onto a
  plugin whose whole job was originally "reconnect me to my own
  wifi."
- Should the DHCP hostname/MAC behavior be tied to a single
  `stealth_mode` boolean, or should MAC randomization and hostname
  spoofing be two independent toggles? They're different concerns
  (device fingerprint vs. DHCP log entry) even though the original
  bundled them together.
- Is polling `wpa_cli status` for real state acceptable, or is there
  a reason to keep the simpler (if slower/less honest) fixed-sleep
  approach - e.g. if `wpa_cli` itself is flaky on this hardware?
  Worth a quick manual test before committing to the rewrite.

## Required tools / dependencies

Same as the original: `macchanger` (now optional per the stealth
toggle), `wpa_supplicant`/`wpa_cli`/`dhclient` (standard on the image
already). If the recon step is built: `nmap` (currently an unused
listed dependency in the original's README - would finally be used)
or `scapy` for a lighter-weight ARP sweep instead.

## Proposed config

See `config-example.toml` in this folder. Not wired to real code yet.
