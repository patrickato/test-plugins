# The God-Drive Manifest

A vetted master list for building "one USB to rule them all" (and a themed fleet
behind it). Every entry is checked as it's added: **official source, latest
version, how to verify it, and whether it's still maintained.** We build the drive
entry by entry — nothing goes on from an unverified mirror.

> **Read `README.md` and `INTERESTS.md` first for context.** This is the USB-fleet
> deep-dive's concrete output. Target use is the user's own gear / authorized work.

## The rules for this list (non-negotiable)

1. **Official source only.** The project's own GitHub releases page or its own
   domain. Never a "download portal," warez mirror, or a result with "crack",
   "keygen", "patched", or "premium unlocked" in the name. (The #1 search hit for
   "MediCat USB" is a malware trap named *"MediCat USB Crack"* — that is the exact
   trap this rule exists for.)
2. **Verify before it goes on the drive.** Match the published **SHA-256** (or
   verify the **GPG signature** where the project signs releases — Tails, Kali,
   Debian do). A download with no checksum you can match doesn't get copied.
3. **Maintained status is tracked.** Dead projects can still be useful (they just
   never get patched), but you should *know* when a tool was last touched.
4. **Version numbers drift; the checksum is the anchor.** The versions below are
   current as of **2026-10-05**. When you actually download, read the version off
   the official page and match *that* page's checksum. Treat the versions here as
   "what to expect," not gospel.

Legend: ✅ actively maintained · 🟡 slow/occasional · 🔴 abandoned (use with eyes open)

---

## Tier 0 — The platform (the drive itself)

| Tool | Official source | Version (2026-10-05) | Verify | Maint. | Notes |
|---|---|---|---|---|---|
| **Ventoy** | github.com/ventoy/Ventoy (releases) | ~1.1.11 | SHA-256 on the release page; releases are also GPG-signed (key in repo) | ✅ | The core. Copy ISOs onto the drive; Ventoy boots any of them from a menu. Secure Boot + persistence supported. This is what makes the NVMe a "god-drive." |

**Ventoy NVMe god-drive recipe:** NVMe SSD in a USB 3.1 enclosure → run Ventoy's
installer once onto it → drop every verified ISO below into the big data
partition. One fast drive, a boot menu of everything. (NVMe-in-enclosure read
speed is the whole reason this beats a stack of flash sticks.)

---

## Tier 1 — Essential ISOs (every god-drive should have these)

| Tool | Purpose | Official source | Version | Verify | Maint. |
|---|---|---|---|---|---|
| **SystemRescue** | Linux rescue/repair toolkit (gparted, fsck, ddrescue, network tools) | system-rescue.org / sysresccd.org | 13.x | SHA-256 + GPG sig on download page | ✅ |
| **Clonezilla Live** | Disk/partition imaging & cloning | clonezilla.org | 3.2.1-28 | SHA-256/SHA-512 on the download page | ✅ |
| **GParted Live** | Dedicated partition editor (resize/move/format) | gparted.org | 1.7.0-8 | SHA-256 + GPG sig on download page | ✅ |
| **memtest86+** | RAM diagnostic (free/GPL build) | memtest.org | 7.20 | SHA-256 on site / GitHub releases | ✅ |
| **Rescuezilla** | "Clonezilla with a GUI" — friendlier imaging | github.com/rescuezilla/rescuezilla | current | SHA-256 on GitHub release | ✅ |

> These five cover 90% of "my machine won't boot / I need to image a disk / is the
> RAM bad / let me fix partitions." Rescue-track foundation.

---

## Tier 2 — The big all-in-one toolkits (Windows-side rescue)

| Tool | Purpose | Official source | Version | Verify | Maint. | Watch for |
|---|---|---|---|---|---|---|
| **Hiren's BootCD PE** | WinPE loaded with Windows repair/diagnostic tools (passwords, partitioning, AV, hardware tests) | hirensbootcd.org | 1.0.3 | SHA-256 on the official site | 🟡 | Only `hirensbootcd.org`. Many copycats. |
| **Medicat USB** | Huge WinPE + portable-apps toolkit (Mini Windows 10, tools galore) | github.com/mon5termatt/medicat_installer | current | checksums via the official GitHub installer | 🟡 | **"MediCat USB Crack" = malware.** Only the mon5termatt GitHub. |
| **Sergei Strelec's WinPE** | WinPE rescue environment, very complete | Strelec's own board (sergeistrelec.name / .ru) | current | **No clean English signed source — treat as untrusted** | 🟡 | Russian-language origin; countless reuploads. If used, sandbox-verify; do not trust random mirrors. Lowest-trust entry here — flagged honestly. |

> Hiren's and Medicat overlap a lot. For a *clean, trustworthy* drive, Hiren's PE +
> SystemRescue is the safer pairing; Medicat is the "everything bucket" if you want
> it. Strelec is powerful but the sourcing is the problem, not the tool — noted so
> you decide with eyes open.

---

## Tier 3 — Offense / security live distros (your tracks)

| Tool | Purpose | Official source | Verify | Maint. | Notes |
|---|---|---|---|---|---|
| **Kali Linux (Live)** | The red-team distro — live or persistent | kali.org/get-kali | SHA-256 **+ GPG** (Kali signs; verify the sig, not just the hash) | ✅ | Live-USB with persistence = portable attack box. Track 11. |
| **Parrot Security** | Kali alternative, lighter, privacy-leaning | parrotsec.org | SHA-256 + signature | ✅ | Good second opinion to Kali. |
| **BlackArch (Live ISO)** | Arch-based, ~2800 tools | blackarch.org | SHA-256 on site | ✅ | Huge toolset; Track 11. Heavier, for when you want *everything*. |
| **Tails** | Amnesic Tor-routed privacy OS | tails.net | **GPG signature (strongly)** — Tails has a guided verify flow | ✅ | Track 10 (Tor/dark web). Runs from USB, leaves no trace. Pairs with the Tor deep-dive. |

> **Verification matters most here.** A tampered Kali or Tails image is the whole
> ballgame. For these four, verify the **signature**, not just a hash copied from
> the same page an attacker could have changed.

---

## Tier 4 — The themed fleet (grouping the rest of your sticks)

Not everything belongs on the one god-drive. The clean split, so each stick has a
job:

- **⚔️ Offense stick** — Kali *or* Parrot live + persistence; your own payloads;
  pairs with Flipper/ESP32 work.
- **🛟 Rescue stick** — Ventoy + SystemRescue + Clonezilla + GParted + memtest +
  Hiren's PE. The "fix anyone's dead machine" drive.
- **🕵️ Privacy stick** — Tails (kept *separate and clean* — don't mix offense tools
  onto the amnesic drive; that defeats the point).
- **🧰 Portable-apps stick** — PortableApps.com platform or the portable set inside
  Medicat; no-boot, runs on a live Windows session.
- **💿 Install stick** — Ventoy with Win10/11 + Debian/Ubuntu/Pi imager ISOs; your
  "set up a new box" drive.
- **🔬 Forensics stick** — read-only mindset: CAINE / Tsurugi / Autopsy live; keep
  this one *write-blocked* in use so you don't taint evidence. (Feeds Track 9 /
  Y-series.)

---

## Build order (what we do next, entry by entry)

1. **Ventoy onto the NVMe enclosure** (Tier 0) — the platform.
2. **Tier 1 five** — rescue foundation, all actively maintained & easy to verify.
3. **Pick Tier 2 pairing** — Hiren's PE (clean) ± Medicat (the everything bucket).
4. **Tier 3 live distros** — Kali + Tails first (your Track 10/11 anchors),
   signature-verified.
5. **Split the rest of your sticks into the Tier 4 themes.**

As we add each one for real, I pull the live version + checksum off the official
page and we verify before it's copied. That's the "check absolutely everything"
promise, made concrete.

---

## Honest scope of "check everything"

What I **can** verify: official GitHub/domain, published SHA-256/SHA-512, GPG
signatures where projects sign, latest version, and maintained status. What I
**can't**: read Discord/gated forums, vouch for random reupload mirrors, or verify
a binary I can't fetch a published hash for. And I won't source from warez/"crack"
sites — that's where the real traps live (the Medicat example above is not
hypothetical). Where a tool's only sourcing is murky (Strelec), I say so instead of
pretending it's clean.
