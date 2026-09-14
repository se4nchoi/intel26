# Architecture

## Ownership and lifecycle

`cli.py` validates settings before `app.py` constructs devices. Imports perform no
hardware I/O. The FastAPI lifespan starts a controller worker and closes devices on
shutdown. Only the RealSense adapter has a separate capture thread, which owns its
camera pipeline and publishes immutable frame copies under a lock.

The controller worker serializes commands and owns the robot and PLC. HTTP handlers
read cached snapshots or enqueue a request. A queue admission flag rejects concurrent
commands instead of allowing double-clicks to create extra cycles. Controlled stop
uses an event that adapters inspect during their bounded polling loops.

```text
Local browser → FastAPI command admission → Controller worker
                       ↑                         │
                  cached status                 ├── SQLite store
                                                ├── Robot adapter
                                                ├── PLC adapter
                                                └── Camera observations
```

Database ownership is enforced for a single database path, not as a distributed lock
on a robot. Deploy one controller process for the physical cell. Do not use multiple
workers or another application that independently commands the same robot.

## Cycle

`DISABLED → READY → INSPECTING → PLANNING → PICKING → VERIFYING_GRIP → PLACING →
VERIFYING_RELEASE → RETREATING → COMPLETE → READY`.

The final pallet slot transitions to `WAITING_FOR_PALLET_CHANGE` instead of READY.
Any execution error latches `FAULT`, disables further cycles, and attempts a controlled
robot stop. An unconfirmed stop is appended to the fault rather than concealed.

The planner validates the current pose and every target before actuation. It verifies
that the gripper starts open and empty, moves vertically to the transfer plane, moves
over the taught pickup fixture, descends, closes and checks grip/part feedback, retracts,
transfers, descends, releases, verifies empty/open feedback, commits placement, and retracts.
It does not open the gripper automatically at cycle start, because that could drop a held part.

The complete route must be physically commissioned, including the first vertical move
from the permitted starting poses. Endpoint bounds do not protect other robot links,
tool geometry, singularities, obstacles, or an unverified approach path.

## Accounting and recovery

Slot states: `EMPTY → RESERVED → OCCUPIED`. A cycle and its reservation are created in
one SQLite transaction. A reservation becomes occupied only after release feedback.
Any earlier execution uncertainty makes the reserved slot `UNKNOWN`. If retreat fails
after placement, the occupied slot remains occupied and the cycle faults.

SQLite uses WAL and FULL synchronization. On restart, RUNNING cycles become INTERRUPTED,
their reservations become UNKNOWN, and a recovery fault is persisted. A previously
latched fault also survives restart. The controller always starts disabled.

An acknowledgment failure after a physically completed placement faults the cycle; it
does not free the occupied slot or issue another pick. Review the journal and PLC state
before acknowledging recovery. Magazine failures require inspecting the magazine and
gripper; they do not create a pallet reservation.

## Timing and failure semantics

Neuromeka generated gRPC stubs receive per-call deadlines. Motion polling checks SDK
response codes, operation state, target-reached state, queue emptiness, and measured
pose for three samples. The SDK's default no-argument wait helper is not used.
Gripper feedback requires open/closed consistency and an independent part-present input.

PLC read/write failures raise faults. A read failure never substitutes a clear emergency
stop or a permissive mock value. Heartbeat freshness is measured on changing values,
not merely successful TCP reads. Run permission is checked between actions and while
waiting for motion/grip feedback. Polling latency includes bounded RPC/network calls;
this Python application is not a hard-real-time or safety-rated controller.

The camera returns a timestamped observation from one RGB-D frame. Missing depth,
multiple candidates, unsupported silhouettes, stale frames, and ROI-edge clipping are
rejected. Once inspection is accepted, the recipe uses a fixed fixture pose. The PLC
must keep the fixture stable throughout the transfer.

## Source layout

| File | Responsibility |
|---|---|
| `models.py` | Device protocols, poses, observations, states |
| `config.py` | Strict TOML models and target validation |
| `controller.py` | Single-owner sequencing, admission, faults, recovery |
| `storage.py` | Durable cycles, inventory, event records, process lease |
| `simulation.py` | Explicit devices and injected failures |
| `hardware.py` | IndyDCP3 and MC Protocol adapters |
| `vision.py` | RealSense capture and conservative fixture inspection |
| `app.py`, `web/` | Local dashboard and command API |
| `cli.py` | Validated startup, simulation demo, serving |

## HTTP contract

`GET /api/status`, `/api/history`, and `/api/frame` are read-only. Device reads happen
on the worker/capture threads, not inside those handlers. The frame handler encodes
the capture thread's latest buffered image, so preview continues during motion.
Camera frames return 503 when
unavailable. Cached telemetry includes monotonic capture timestamps; it is not evidence
that a device is currently healthy if the worker or dashboard is stale.

`POST /api/commands` requires the `X-Workcell-Token` served in the local dashboard's meta
tag. A 202 response means accepted/requested, not completed. Inspect `last_command`,
cell state, and the cycle journal for the outcome. Invalid command admission returns 409;
invalid recovery fields return 422. The dashboard does not expose arbitrary pose commands,
servo activation, joint homing, or an in-session hardware-mode toggle.
