# The Hacker's Atlas — full field map

A complete, handled map of offensive security / red teaming, built as a learning
roadmap. Peg items by their handle (e.g. `C4`, `K7`, `E1-9`). This is the *field
map*; `INTERESTS.md` tracks what's been picked.

> **Ground rule for everything below:** these are learning/field-mapping entries.
> When we actually BUILD or RUN something, it's on the user's own gear or
> explicitly authorized targets. Understand-and-defend is always on the table;
> weaponized artifacts aimed at non-consenting third parties are not. The user
> endorsed this himself: *"the user must choose to do wrong... keep the friction."*

## A — Foundations & mindset
A1 networking deep (TCP/IP, routing, switching, VLANs) · A2 OS internals · A3 attacker mindset / threat modeling · A4 kill chain & MITRE ATT&CK · A5 scripting for hackers (Python/Bash/PowerShell) · A6 lab building / virtualization / snapshots · A7 note-taking & methodology discipline

## B — Recon & OSINT
B1 passive recon (whois, DNS, cert transparency) · B2 Google/GitHub dorking · B3 people-OSINT (usernames, breaches, social) · B4 corporate footprinting (ASNs, subdomains, tech stack) · B5 Shodan/Censys/ZoomEye · B6 metadata & document intel · B7 geolocation / image OSINT · B8 recon automation pipelines

## C — Network attacks
C1 scanning & enumeration (nmap mastery) · C2 service exploitation · C3 MITM / ARP / DNS spoofing · C4 Responder / LLMNR-NBT-NS poisoning / relay · C5 pivoting & tunneling (SOCKS, port-forward, chisel) · C6 VPN & firewall attacks · C7 protocol abuse (SNMP/SMB/RDP) · C8 VoIP/SIP · C9 IPv6 attacks

## D — Web application hacking
D1 OWASP Top 10 · D2 SQLi · D3 XSS · D4 SSRF · D5 auth/session · D6 IDOR/access control · D7 file upload → RCE · D8 deserialization · D9 XXE · D10 API (REST/GraphQL) · D11 JWT · D12 CSRF · D13 SSTI · D14 cache poisoning · D15 bug-bounty methodology

## E — WiFi
E1 WPA2 handshake capture & crack · E2 PMKID · E3 WPA3/SAE · E4 evil twin / rogue AP · E5 captive portal · E6 deauth/disassoc (authorized) · E7 WPS · E8 enterprise (802.1X/EAP) · E9 wardriving & mapping

## F — Bluetooth / BLE
F1 BLE recon & GATT enum · F2 sniffing (Ubertooth/nRF) · F3 BLE replay/relay · F4 pairing/bonding attacks · F5 tracker tech (AirTag/Tile) · F6 classic BT · F7 BLE HID injection

## G — RF / SDR / signals
G1 SDR fundamentals (HackRF/RTL-SDR) · G2 capture/replay (garage/remotes) · G3 sub-GHz (433/315/868) · G4 rolling codes & keyfobs · G5 GPS/GNSS (spoof/jam concepts) · G6 ADS-B/aircraft · G7 AIS/maritime · G8 pagers/POCSAG · G9 cellular (IMSI concepts/GSM) · G10 RFID/NFC (125kHz & 13.56MHz) · G11 decoding unknown protocols (URH)

## H — Hardware hacking
H1 UART/JTAG/SWD · H2 SPI/I2C flash dumping · H3 firmware extraction & analysis · H4 chip-off/desolder · H5 glitching / fault injection · H6 side-channel (power/timing) · H7 PCB RE · H8 logic analyzers & scopes · H9 bus sniffing

## I — Physical red teaming
I1 lock picking · I2 bypass (shims, under-door, latch) · I3 RFID badge cloning · I4 tailgating & pretexting · I5 covert entry tooling · I6 elevator/door controller attacks · I7 camera/alarm evasion concepts · I8 drop boxes / physical implants

## J — Social engineering
J1 phishing (email) · J2 spear-phishing & pretexting · J3 vishing · J4 smishing · J5 pretext development · J6 OSINT-driven targeting · J7 payload delivery & lure design · J8 physical SE / impersonation · J9 influence psychology

## K — Windows & Active Directory
K1 Windows internals · K2 local priv-esc · K3 credential dumping (LSASS/SAM/DPAPI) · K4 Kerberos attacks (kerberoast, AS-REP, delegation) · K5 BloodHound / attack-path mapping · K6 lateral movement (PtH/PtT/WMI/WinRM) · K7 AD persistence (golden/silver tickets) · K8 GPO abuse · K9 ADCS attacks · K10 Windows defense evasion basics

## L / M — Linux & macOS
L1 Linux priv-esc (SUID/sudo/cron/caps) · L2 container escapes · L3 kernel exploits (concept) · L4 Linux persistence · L5 log/artifact awareness · M1 macOS internals · M2 macOS priv-esc & TCC · M3 macOS persistence · M4 Apple security model

## N — Cloud
N1 AWS (IAM/S3/metadata-SSRF) · N2 Azure/Entra ID · N3 GCP · N4 cloud priv-esc & lateral · N5 serverless abuse · N6 cloud persistence · N7 cloud recon/enum · N8 CI/CD & secrets

## O — Containers & orchestration
O1 Docker attacks/escapes · O2 Kubernetes (RBAC/etcd/kubelet) · O3 registry/supply-chain · O4 runtime evasion

## P — Mobile
P1 Android pentest · P2 iOS pentest · P3 RE (Frida/Objection) · P4 SSL-pinning bypass · P5 mobile malware analysis · P6 rooting/jailbreak internals · P7 MDM attacks · (edges: baseband/SMS, app-store abuse, mobile C2)

## Q / R / S — IoT, OT, automotive
Q1 IoT firmware analysis · Q2 IoT protocols (MQTT/CoAP/Zigbee/Z-Wave) · Q3 embedded exploitation · R1 ICS/SCADA (Modbus/DNP3) · R2 PLC attacks · R3 OT safety/ethics · S1 CAN bus · S2 automotive keyless · S3 ECU/telematics · S4 TPMS

## T / U — Crypto & credentials
T1 applied cryptography · T2 crypto attacks (padding oracle, weak RNG) · T3 hash cracking theory · T4 TLS/PKI attacks · U1 hashcat mastery · U2 wordlists & rules · U3 password spraying · U4 credential stuffing (concept/defense) · U5 rainbow tables & GPU rigs

## V / W — Malware & exploit dev  *(study / RE / own-lab framing)*
V1 malware analysis (static/dynamic) · V2 reverse engineering (Ghidra/IDA) · V3 sandboxing/detonation · V4 unpacking/deobfuscation · V5 YARA rules · W1 assembly & memory · W2 buffer overflows · W3 ROP · W4 heap exploitation · W5 format strings · W6 fuzzing · W7 shellcoding concepts · W8 kernel exploitation

## X — Post-exploitation / C2 / evasion  *(understand + defend)*
X1 C2 frameworks (how they work) · X2 persistence techniques · X3 AV/EDR evasion concepts · X4 living-off-the-land (LOLBins) · X5 data exfiltration channels · X6 tunneling & covert comms · X7 implant design concepts · X8 anti-forensics (and how DFIR beats it)

## Y / Z — Defense, forensics, purple
Y1 digital forensics (disk/memory/network) · Y2 incident response · Y3 memory forensics (Volatility) · Y4 log analysis & SIEM · Y5 threat hunting · Z1 detection engineering · Z2 Sigma/Suricata/Snort rules · Z3 purple teaming · Z4 deception/honeypots · Z5 malware triage

## AA — AppSec & supply chain
AA1 secure code review · AA2 SAST/DAST · AA3 dependency/supply-chain attacks · AA4 CI/CD security · AA5 fuzzing harnesses

## BB — AI/ML security
BB1 prompt injection & jailbreaks · BB2 model extraction/inversion · BB3 data poisoning · BB4 adversarial examples · BB5 LLM app pentest · BB6 AI red teaming

## CC — Web3 / blockchain
CC1 smart-contract auditing (reentrancy etc.) · CC2 DeFi exploits · CC3 wallet/key security · CC4 blockchain forensics

## DD–GG — Niche & weird
DD1 game hacking & anti-cheat RE · EE1 mainframe/AS400 · FF1 satellite/space · FF2 GPS internals · GG1 printer/MFP attacks · GG2 smart-home · GG3 medical devices · GG4 POS/ATM (concept/defense) · GG5 drones/UAV

## HH — Covert & exfil
HH1 steganography · HH2 covert channels · HH3 DNS/ICMP exfil · HH4 data hiding & timing channels

## II — OPSEC & infrastructure
II1 operator OPSEC · II2 anonymity (Tor/VPN chains) · II3 redirectors & C2 infra · II4 domain fronting concepts · II5 attribution & counter-attribution

## JJ–LL — Craft & career
JJ1 engagement scoping & ROE · JJ2 report writing (the real product) · JJ3 evidence & note discipline · KK1 CTFs (jeopardy/attack-defense) · KK2 wargames (HTB/OverTheWire/PortSwigger) · KK3 building a practice range · LL1 cert path (eJPT→PNPT→OSCP→OSEP/CRTO) · LL2 home-lab portfolio · LL3 con/community scene · LL4 bug bounty as a career on-ramp
