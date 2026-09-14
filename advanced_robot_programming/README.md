# Neuromeka workcell

A Python 3.12 / uv workcell controller for a Neuromeka Indy robot, RealSense D435,
and Mitsubishi MC Protocol PLC. It runs a complete fixed-pick sorting and palletizing
workflow in simulation, with explicit hardware observation and gated automatic modes.

**Default startup connects to no hardware.** This is an implemented and tested
software foundation, not a commissioned physical cell. Candidate poses and I/O
addresses must be verified on your equipment before automatic operation.

## Run

```powershell
uv sync --python 3.12
uv run workcell --config config/cell.toml validate
uv run workcell --config config/cell.toml serve
```

Open [the local dashboard](http://127.0.0.1:9000). Click **Enable cell**, then
**Start cycle**. Red cubes consume pallet slots; blue cylinders go to the magazine.
Simulation controls can inject missing parts, stale images, disconnects, and motion
or gripper failures. An eight-part pallet never wraps into occupied slots.

For a terminal-only demonstration with an in-memory database:

```powershell
uv run workcell demo --cycles 8
```

The dashboard binds only to `127.0.0.1`. Do not run multiple Uvicorn workers, use
reload mode with hardware, or start another controller against the same physical cell.

## What is implemented

- One controller worker owns all robot and PLC calls. Web requests enqueue commands;
  telemetry stays responsive while motion executes.
- Explicit cycle states, input freshness checks, bounded SDK calls, checked motion
  responses, pose-based completion verification, and independent gripper feedback.
- SQLite cycle history and pallet reservations. Failed/interrupted reservations become
  `UNKNOWN`; confirmed placements remain `OCCUPIED`. Recovery requires inspection and
  explicit reconciliation, followed by a separate enable command.
- A versioned MC Protocol contract with run permission, emergency-stop status,
  changing heartbeats, request IDs, acknowledgments, and completion IDs.
- RealSense RGB-D acquisition and conservative inspection of a single supported
  colored silhouette inside a configured region. No hardware-to-mock fallback.
- A local operator dashboard with camera view, inventory, simulation controls, recovery
  records, and cycle history. Commands require a per-process token from the local page.
- Neuromeka SDK **3.4.2.2**, with adapter behavior checked against its installed source.

## Operating modes

| Mode | Device behavior | Cycle commands |
|---|---|---|
| `simulation` | Explicit simulated robot, PLC, and camera | Enabled after operator enables the cell |
| `observe` | Real reads; no robot actuation or PLC writes | Rejected |
| `automatic` | Real devices, including motion and PLC writes | Requires commissioning gates and operator enable |

Read-only hardware observation is an explicit action:

```powershell
uv run workcell --config config/cell.toml serve --mode observe
```

A mode override uses a separate database named after that mode. It does not mix
simulated pallet inventory into physical inventory. Device startup failures remain
visible; correct the cause and restart the application. There is no synthetic fallback.

Automatic startup requires a reviewed configuration containing `commissioned = true`
and a nonempty `commissioning_reference`, plus the explicit CLI flag:

```powershell
uv run workcell --config config/commissioned-cell.toml serve --mode automatic --allow-motion
```

No commissioned configuration is supplied. Follow [commissioning.md](docs/commissioning.md).
The application never enables servos, clears controller faults, or performs automatic
joint homing. Application workspace checks are endpoint bounds, not full robot/tool
collision checking. The controlled-stop button is not a hardware emergency stop.

## Recovery

1. Correct the actual fault and inspect the gripper, fixture, and destination.
2. With the cell disabled, record an inspection note in the recovery panel.
3. Reconcile each `UNKNOWN` slot as physically occupied or empty.
4. Acknowledge the fault. The cell remains disabled until **Enable cell** is requested.

In simulation, clear the injected failure first. Acknowledging recovery also models
the operator clearing/opening the simulated gripper. Hardware recovery never moves
the robot or changes gripper outputs.

For a full pallet, record that an empty replacement has been installed, then enable
the cell again. Never delete the database to bypass physical inventory reconciliation.

## Configuration and persistence

The checked-in [cell.toml](config/cell.toml) is a simulation recipe. Coordinates are
millimeters and degrees; all configuration keys are validated and unknown keys are rejected.
Relative database paths resolve against the configuration file, not the shell directory.

Databases are bound to a configuration hash. A changed recipe/mode cannot silently
reuse old inventory. Archive the old database and use a new path only after physically
reconciling the cell. A file lease prevents two processes using the same database.
The original project is preserved in [reference/legacy-project.zip](reference/legacy-project.zip);
the original GX Works project remains under `plc/`. Neither is a validated deployment.

## Verify

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
```

Tests use simulated devices or strict SDK/MC doubles. They do not connect to hardware.
They cover cycle accounting, failure propagation, stop/interlock behavior, crash recovery,
configuration validation, HTTP command admission, SDK contracts, and vision rejection cases.

## Design and limits

See [architecture.md](docs/architecture.md), [plc-contract.md](docs/plc-contract.md),
and [commissioning.md](docs/commissioning.md).

This release picks at a taught fixture position. Vision selects the route; it does not
locate an arbitrary pickup pose. The image classifier's quality score is a geometric
heuristic, not a calibrated probability or proof of 3D shape. Camera-to-robot calibration,
variable-position picking, learned recognition, and collision-aware path planning are
separate future capabilities. Physical accuracy, cycle reliability, and PLC ladder behavior
have not been validated by the offline tests.
