# MC Protocol contract, version 1

This is a **new contract**. The previous `plc/mc_protocol.gxw` has not been edited,
compiled, downloaded, or verified against it. Adapt and commission the PLC ladder
before automatic operation. Observation mode never writes PLC memory.

Transport: Mitsubishi Q-series, binary MELSEC 3E using `pymcprotocol.Type3E`, configured
TCP port (sample 5010). This release deliberately has one PLC protocol.

## PLC-owned inputs

| Device | Meaning |
|---|---|
| M0 | Run permit: all fixture/route/process interlocks satisfied |
| M1 | Emergency-stop status: 1 prevents/interrupts application operation |
| D100 | Heartbeat counter; change at least every 500 ms, range 0–32767 |
| D101 | Cycle request ID; 0 = no request, 1–32767 = a new unique request |
| D102 | Contract version: must equal 1 |

Run permit must cover part fixture retention, required destination readiness (including
magazine capacity), machine/process readiness, and any PLC-controlled equipment whose
movement would invalidate the commissioned path. It must remain valid throughout the
cycle. The Python implementation does not write or clear these input devices.

A successful read alone is insufficient: permission stays false until the heartbeat
has changed once. An unchanged heartbeat beyond `heartbeat_timeout_s` faults the cell.
Configure PLC-side PC-heartbeat supervision as well. M1 is application status only;
physical emergency-stop wiring must independently perform its required safety function.

## PC-owned outputs

Written together as six signed 16-bit words:

| Device | Meaning |
|---|---|
| D110 | Accepted/current request ID (0 for manual dashboard cycles) |
| D111 | State code from the table below |
| D112 | Active pallet slot, zero-based; -1 when no pallet slot is active |
| D113 | Last completed PLC request ID; retained during later idle states |
| D114 | Fault flag: 1 = latched fault |
| D115 | PC heartbeat counter, wraps at 32768 |

| Code | State | Code | State |
|---|---|---|---|
| 0 | DISABLED | 6 | PLACING |
| 1 | READY | 7 | VERIFYING_RELEASE |
| 2 | INSPECTING | 8 | RETREATING |
| 3 | PLANNING | 9 | COMPLETE |
| 4 | PICKING | 10 | WAITING_FOR_PALLET_CHANGE |
| 5 | VERIFYING_GRIP | 11 | FAULT |

The PC heartbeat advances on status publications, including guarded motion polling.
Its interval includes network/RPC latency. Establish PLC supervision timeouts from
measured worst-case behavior and the independently implemented safety system.

## Request sequence

1. Hold D101 at zero after PC startup or enable. The controller does not accept a request
   already high at startup/enable.
2. When READY with M0 true and M1 false, set D101 to a new nonzero request ID. Keep the
   fixture stable and maintain permit for the whole cycle.
3. Observe D110 for acknowledgment. Completion requires matching D113 and no fault;
   D110 acknowledgment alone does not mean success. Do not rely on seeing transient
   state 9, since the controller subsequently reports READY/full pallet.
4. Return D101 to zero. Use a different ID for the next cycle. A sustained request never
   retriggers, and the last consumed ID is persisted across PC restarts.
5. On a fault, reconcile the physical outcome before submitting any new request. The PC
   will not automatically retry interrupted or failed motion.

Manual dashboard start requires D101=0. Manual cycles publish request ID 0 and do not
change the last completed PLC request ID. The PLC must treat them accordingly.

No ladder code is synthesized from undocumented wiring. The precise run-permit logic,
sensor polarity, heartbeat supervision, ownership of fixtures, and destination availability
must be verified in the actual PLC program during commissioning.
