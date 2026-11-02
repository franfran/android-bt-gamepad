# I2/I6 — Offline cable-session state-machine prototype

Files:
- `experiments/m3-ds3-cable-session/ds3_session_model.py`
- `experiments/m3-ds3-cable-session/test_ds3_session_model.py`

Run from the repo root:

```bash
cd experiments/m3-ds3-cable-session
python3 -m unittest -v
```

**Execution result (isolated local container, Python 3): 10 tests passed.** No Bluetooth stack or device involved.

Modelled transitions: `UNENROLLED → ENROLLED → ACL → CONTROL(0x11) → BOTH_CHANNELS(0x13) → JAVA → ACTIVE`. Any fresh ACL connect increments the epoch; disconnect invalidates old tokens; adapter change/revocation invalidates enrollment; Java quiet mode or forbidden policy fails closed; UHID stage requires explicitly simulated completed report.

**CRITICAL LIMITATION:** `trusted_peer_proven=True` is intentionally a *symbolic test oracle*. Real DS3 cable enrollment does not by itself provide cryptographic proof that a radio peer owns the enrolled MAC. No real mechanism to establish this predicate has been implemented or demonstrated. It is invalid to wire this prototype to a simple MAC/name/CoD check and declare it secure.

Other limitations: no actual ACL/CCB generation, native callback delivery, async event queue, concurrent sessions, Android persistent record, Java authorization bridge, Bluetooth security or UHID report exchange. Enforced control-before-interrupt ordering is a **proposed model assumption**, not a live DS3 packet sequence guarantee. These tests establish model internal consistency only, not implementation correctness or safe authorization.

**Owner-established acceptance:** wired USB DS3 already works with RetroArch on M3; one-time USB enrollment is acceptable, wireless Bluetooth gameplay/reconnect after cable removal is required.

Next milestone: prove source-level pre-auth authorization feasibility and a defensible trust/risk model before adapting this state machine into Fluoride. No M3 operations or runtime changes authorized. PR #50/#51 remain separate.
