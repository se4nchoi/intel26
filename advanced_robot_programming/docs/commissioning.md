# Physical commissioning boundary

The software has been verified offline. No hardware connections, robot moves, PLC
writes, or calibration measurements were performed as part of this rebuild.

`config/cell.toml` contains candidate coordinates copied from the old project. Its
workspace box and transfer height are examples, not measured collision clearance.
There is intentionally no supplied `commissioned-cell.toml`.

## Establish the actual cell

Record robot model/controller firmware, SDK version, TCP/tool transform, payload,
gripper geometry, fixture/table geometry, taught poses, and relevant PLC project revision.
Verify the installed SDK with the actual controller. The current adapter uses IndyDCP3
millimeters/degrees and SDK 3.4.2.2; no older DCP2 assumptions are shared.

Document emergency-stop and protective-device wiring separately from application
status bits. The application cannot establish the integrity of that system.

Verify the complete pick/transfer/place/retreat path, including the initial move from
each permitted starting pose. Use the robot's established teach-pendant commissioning
procedure; the dashboard does not expose arbitrary jogging, servo activation, or joint
home commands. Clearances must include the robot links, tool, held part, pallet layers,
magazine, and other fixtures. Endpoint bounds alone do not check those clearances.

## Verify the gripper and process feedback

The current adapter assumes one binary close/open output and three distinct inputs:

- `close_do`: one output whose configured active state closes the gripper.
- `closed_di`: closed/grip-position feedback.
- `open_di`: open-position feedback.
- `part_present_di`: independent indication that a part is held.

All three feedback inputs use `feedback_active_high`; the output has independent
`close_do_active_high`. A missing input or contradictory feedback times out.
Closed position alone is not accepted as evidence of a held part. Verify that the
actual sensors have these semantics for both supported parts. If your gripper uses
two solenoids, analog/vacuum feedback, controller end-tool I/O, or another wiring
pattern, implement and test that adapter before enabling automatic mode.

At cycle start the gripper must already be open and empty. Recovery requires physically
clearing the gripper/fixture when appropriate; fault acknowledgment never actuates it.
Open/empty feedback establishes release, not the precise final placement of the part.
Add destination sensing if the process needs independent placement verification.

## Verify PLC and vision

Implement and validate [the MC contract](plc-contract.md) in the actual ladder.
Check inputs, counter changes, version word, permission loss, read/write failures,
request acknowledgment, completion, full pallet, and PC restart behavior. Use a single
PC controller instance; the retained GX Works binary is a reference, not a deployment.

In observation mode, verify camera orientation, ROI, lighting, depth coverage, and the
repeatable pickup fixture. Test actual red cubes and blue cylinders at all permitted
orientations. The classifier recognizes color and visible silhouette; it is not general
3D recognition. Its score is a heuristic. Record labeled workcell frames, rejection
rates, and misclassification rates before relying on it for routing.

The camera does not adjust the pickup coordinate. The fixture must constrain position
and orientation to the taught grip tolerance and stay fixed throughout each cycle.

## Record and validate the commissioned configuration

1. Copy the sample configuration to `config/commissioned-cell.toml` and select a new
   database path for the physical cell. Record actual poses, bounds, I/O, and timeouts.
2. Run `uv run workcell --config config/commissioned-cell.toml validate`. This validates
   software constraints only; it does not connect to hardware or certify the path.
3. Use `serve --mode observe` to inspect real status without motion or PLC writes.
4. Complete physical commissioning with qualified operators and record evidence in a
   local commissioning report. Set `commissioning_reference` to that report/revision
   and `commissioned = true` only when its checks are actually complete.
5. Start automatic mode explicitly with `serve --mode automatic --allow-motion`.
   Startup remains disabled. Enable only after checking the workcell's current condition.

Before routine operation, demonstrate controlled behavior for failed grip, missing part,
camera loss before inspection, PLC permission loss, network interruption, failed retreat,
full pallet, application shutdown during transfer, and application restart. Reconcile
inventory and held-part uncertainty rather than clearing records to obtain READY.

## Future variable-position pickup

This requires calibrated camera-to-robot extrinsics, verified intrinsics/depth accuracy,
TCP/tool calibration, object orientation estimation, grasp feasibility, and measured
end-to-end position error. Add it as a separate recipe/planner once fixed-pick operation
has a measured reliability baseline. Never clamp an invalid estimated pose into the workspace.
