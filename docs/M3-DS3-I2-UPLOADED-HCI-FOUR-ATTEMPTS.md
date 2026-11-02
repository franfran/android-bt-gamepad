# I2 — Direct uploaded HCI evidence: four PIN-request timeouts

**Evidence reviewed offline:** owner-supplied `btsnoop_hci(2).log`, rotated `btsnoop_hci.log(2).last`, `ds3-pairing-diagnostic.txt`, and `ds3-pairing-raw.log`. Raw logs and device addresses MUST NOT be committed. All times below: btsnoop timestamps in UTC as encoded by file (not necessarily Android logcat timezone).

## Direct packet-level result
The main H4 btsnoop file parses as 1,789 records from 2026-10-28 23:40 UTC to 2026-10-30 01:01 UTC. **Four separate DS3 connections** show:
1. HCI Connection Complete success (event 0x03).
2. Host command `Authentication Requested` (opcode `0x0411`).
3. Controller event `Link Key Request` (event `0x17`), then host command `Link Key Request Negative Reply` (opcode `0x040C`).
4. Controller event `PIN Code Request` (event `0x16`).
5. **No observed host PIN Code Request Reply command** (opcode `0x040D`) nor Negative Reply command (`0x040E`) in this captured main HCI log during these intervals.
6. HCI Authentication Complete event `0x06`, status `0x22` = LMP Response Timeout, approximately **30.06 seconds after PIN request**, followed by disconnect event `0x05` reason `0x22`.

Four event windows, sanitized (no MAC/link key):
| Attempt | Authentication Requested (UTC) | PIN Code Request (UTC) | Authentication Complete 0x22 (UTC) | PIN→timeout |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-29 17:11:54.243 | 17:11:54.247 | 17:12:24.308 | 30.061 s |
| 2 | 2026-10-29 17:12:24.922 | 17:12:24.927 | 17:12:54.988 | 30.061 s |
| 3 | 2026-10-30 00:57:19.110 | 00:57:19.120 | 00:57:49.188 | 30.067 s |
| 4 | 2026-10-30 00:57:56.025 | 00:57:56.034 | 00:58:26.098 | 30.063 s |

The rotated `.last` file is a **different earlier capture segment** (2026-10-28 23:32–23:39 UTC, only 106 records), with no DS3 PIN request evidence. Do not merge or order its timestamps as part of the main pairing sessions.

## Android logcat — separate capture day
Owner-supplied diagnostic text shows **2026-10-31** attempts at approximately 11:54:23 and 11:54:55 logcat clock:
- `pinRequestCallback`, name `PLAYSTATION(R)3 Controller`, CoD `0x0508`.
- `BluetoothPairingRequest: onPair: null` shortly afterward (twice).
- For first attempt, bonding switches to NONE ~30 seconds after request with status 10.
These **support recurring null-PIN handling**, but are **not the same timestamped attempt** as Oct 29–30 btsnoop sessions; do not claim cross-source synchronized packet correlation. Only the within-HCI sessions are fully correlated.

## What is proven vs not
**PROVEN:** HCI authentication was requested; controller link key request received negative reply; controller requested a PIN; captured host never answered PIN at HCI command level; timeout 0x22 follows ~30s in four intact sessions. This is a more discriminating initial failure signature than generic 'security rejection' or Java HID rejection. The 2026-10-31 Android diagnostic independently identifies `onPair: null` and lack of bonded outcome.

**INFERRED (strong):** Missing PIN response is a leading causal hypothesis for these timeouts and an immediate engineering blocker. The handler defect and HCI symptom are consistent.

**UNPROVEN:** Valid DS3 PIN bytes or whether DS3 can/should pair through ordinary legacy PIN; that `onPair: null` occurred during the Oct 29/30 HCI sessions; that sending any PIN completes authentication; equivalence to a signed/authorized USB enrollment; native/Java/UHID later-stage fixes. Do not use guessed PIN or fake bond state.

## Decision impact
- Historical HCI **evidence gap is partly CLOSED**: there are four timestamped within-session HCI traces; previous claim that no continuous HCI capture is available must be superseded.
- Plugin/daemon implementation remains premature; the first observable break is **HCI PIN-request handling / legacy authorization**, before HID Host Java admission and UHID.
- Next offline milestone: identify the *protocol-correct* DS3 authentication method from appropriate implementations and exactly which M3 Android API can implement it without global security downgrade. Build read-only negative/safety cases; no runtime pairing without Owner approval.

## Privacy
Do not publish raw btsnoop, real MACs, PIN, link keys, addresses, ACL dumps or raw logcat. This document contains only protocol metadata and timestamps. No M3 commands executed.
