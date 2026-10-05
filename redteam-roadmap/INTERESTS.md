# Pegged interests — organized into tracks

Handles reference `ATLAS.md`. Status: **pegged** = he picked it; **candidate** =
Claude suggested, awaiting his yes; **deep-dive queued** = agreed to discuss soon.

## Agreed discussion order (then revisit the list)
1. **Flipper Zero — all things** ← current
2. Tor + deep/dark web
3. The USB fleet (BadUSB payload library on top of badhid)
4. Kali / BlackArch — guided toolchain tours
5. Revisit the full list, turn tracks into a build+learn plan

## Track 1 — Recon & OSINT
A5 scripting · B2 dorking · B3 people-OSINT · B7 geo/image OSINT · B8 recon automation

## Track 2 — Wireless & RF toys  *(his biggest track; Flipper lives here)*
E1 WPA2 capture/crack · E2 PMKID · E3 WPA3 · E4 evil twin · E5 captive portal · E6 deauth (authorized) · E7 WPS · E9 wardriving  *(NOT E8 enterprise)*
F1–F7 all Bluetooth/BLE
G2 capture/replay · G3 sub-GHz · G4 rolling codes/keyfobs · G5 GPS concepts · G8 pagers · G10 RFID/NFC
+ **Flipper Zero** (deep-dive queued #1)

## Track 3 — Hardware
H1 UART/JTAG/SWD · H3 firmware extraction

## Track 4 — Physical
I6 elevator/door controllers · I7 camera/alarm evasion

## Track 5 — Windows & cross-network control  *(core professional track)*
A4 kill chain/ATT&CK · C1 scan/enum · C2 service exploit · K1 Win internals · K2 local priv-esc · K3 credential dumping · L1 Linux priv-esc · L3 Linux kernel (concept)
+ **cross-network control** (one box controlling another across networks/NAT: C5 pivoting + X1 C2 + reverse shells + legit mesh like Tailscale/SSH/RMM)
+ platform focus: **Windows 10/11** and **Pi 4/5**

## Track 6 — USB / BadUSB fleet  *(deep-dive queued #3)*
BadUSB wired + wireless · a fleet of USBs that each do something cool · script-running · builds on complete-plugins/badhid-ng

## Track 7 — Mobile
Full P set (P1–P7 + edges). "Mobile hacking interests me."

## Track 8 — Cracking
U1 hashcat mastery

## Track 9 — Offensive AI & oddballs
BB1 prompt injection · BB6 AI red teaming · DD1 game hacking/anti-cheat · GG4 POS/ATM (concept) · GG5 drones · HH2 covert channels

## Track 10 — Tradecraft & anonymity  *(deep-dive queued #2)*
Tor + deep/dark web (mechanics, OPSEC, reality vs myth)

## Track 11 — Toolchain mastery  *(deep-dive queued #4)*
Kali & BlackArch guided tours ("the 20% of tools used 80% of the time," then deeper); complete toolchains that make long/tedious/hard tasks a breeze

---

## Candidate additions (Claude suggested — awaiting his yes)
- **K4–K9** Active Directory attack paths (Kerberoast, BloodHound, lateral, golden tickets) — core of modern red teaming
- **C4 + C5** Responder/relay + pivoting/tunneling — feeds the cross-network dream
- **X1–X8** post-ex / C2 / evasion (understand+defend)
- **J1/J2/J5** social engineering (phishing + pretexting) — he pegged none; it's half of red teaming
- **G11** decode unknown protocols with URH — peak "point-click-results" RF
- **KK2/KK3** CTF ranges + build a practice range — the legal playground for all of it
- **I1 + I3** lockpicking + RFID badge cloning — rounds out the thin physical track
- **Z3** purple teaming — watching your own attacks get caught makes you a better attacker

## His relevant gear (for build targeting)
Win10/11 PCs · several Raspberry Pis (incl. Pi4/Pi5) · a couple old Android phones · USB SDR · HackRF One + PortaPack (AliExpress) · Flipper Zero + attachments · various ESP32 boards (pair with Flipper for WiFi via Marauder) · old Win XP/7-era boxes for destructive/forensics labs
