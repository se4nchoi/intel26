"""
Final Exam - Indy7 Feeder -> 5x5 Pallet Pick & Place (Vacuum on DO 2)
=====================================================================

Positions: latest jog points from the neuromeka-digitaltwin teach pendant
(data/positions.csv, saved 2026-11-16 10:18, robot 192.168.3.7):
    pick-feed, place-1, place-2, place-6

Trajectory mimics the digital-twin palletizing cell:
    Home            MoveJ  (joint)
    Feeder approach MoveJ  -> IK of the approach, seeded with pick-feed joints
    Feeder pick     MoveL  100 mm plunge along the tilted tool axis,
                           last 6 mm creeping slowly
    Feeder retract  MoveL  first 6 mm creeping, then back out the same line
    Pallet approach MoveJ  -> IK of slot approach, seeded with place-1 joints
    Pallet place    MoveL  100 mm straight down
    Pallet retract  MoveL

Sequence
--------
1) Move HOME
2) Feeder (미끄럼틀) pick APPROACH
3) Pick location move
   3-1) Vacuum ON (DO 2) at magazine point
4) Pick RETRACT
5) Pallet #N place APPROACH
6) Place location move
7) Vacuum OFF (DO 2)   (+ place RETRACT)
8) Repeat 2-7 for pallet #4, #8, #10   ->  places: 2, 4, 8, 10
Finally return HOME.

Pallet numbering (~40 mm pitch, 3-point taught: place-1, place-2, place-6)
--------------------------------------------------------------------------
     1   2   3   4   5        col -> (place-2 - place-1)  ~ -Y 40.8 mm
     6   7   8   9  10        row -> (place-6 - place-1)  ~ -X 41.0 mm
    11  12  13  14  15
    16  17  18  19  20
    21  22  23  24  25

Usage
-----
    uv run python final_exam.py            # run on the real robot
    uv run python final_exam.py --dry-run  # print all targets, no robot connection
    uv run python final_exam.py --teach    # print current q / p (to re-teach)
"""

import math
import sys
import time
from typing import Dict, List

from neuromeka import IndyDCP3, JointBaseType, OpState, TaskBaseType

# ==============================================================================
# ROBOT / IO CONFIG
# ==============================================================================
ROBOT_IP = "192.168.3.7"
ROBOT_INDEX = 0

VACUUM_DO = 2                  # 흡착 on/off -> robot digital output d2

# Faster top speed (+60 %) with a lower acceleration ratio: the robot reaches
# speed quickly enough but brakes over a long ramp, so it glides into each
# approach / retract point instead of stopping hard.
TRANSIT_VEL, TRANSIT_ACC = 40, 20   # MoveJ transits to the approach points (was 25 / 25)
ACTION_VEL, ACTION_ACC = 25, 12     # MoveL plunge / retract (was 15 / 15)

APPROACH_DIST = 100.0          # mm back-off along the tool axis for approach / retract
VACUUM_DWELL = 0.5             # s to let suction release on the pallet
PICK_VACUUM_DWELL = 0.9        # s to let suction fully seal before lifting off the feeder

# Feeder pickup: the part has play in the slide, so the last / first few mm at
# the magazine point are slow to seat and lift it the same way every time.
FEED_CREEP_DIST = 6.0          # mm along the tool axis (was 15)
FEED_CREEP_VEL, FEED_CREEP_ACC = 12, 20   # was 6 / 6 (~6 s total) -> ~1 s total
MOVE_TIMEOUT = 60.0            # s per motion

# ==============================================================================
# TAUGHT JOG POINTS  (neuromeka-digitaltwin data/positions.csv, 2026-11-16)
# task [X, Y, Z (mm), U, V, W (deg)] / joint [q1..q6 (deg)]
# ==============================================================================
# Feeder (미끄럼틀) magazine point - tool tilted ~20 deg to the slide
PICK_FEED = [202.96, 487.47, 149.46, -0.36, -159.86, 0.17]
PICK_FEED_Q = [70.99, -32.2, -67.85, 19.13, -86.66, 68.62]

# Pallet 3-point teach
PLACE_1 = [196.08, 335.98, 195.56, 0.09, -179.96, 0.01]
PLACE_1_Q = [88.33, -1.55, -107.83, 0.04, -70.71, 88.3]
PLACE_2 = [196.18, 295.19, 197.93, 0.14, -179.95, 0.01]   # next column
PLACE_6 = [155.11, 335.57, 195.87, 0.28, -179.95, 0.05]   # next row

# Grid geometry: steps measured from the taught points
PALLET_COLS = 5
PALLET_ROWS = 5
COL_STEP = [PLACE_2[i] - PLACE_1[i] for i in range(3)]   # (dx, dy, dz) 1 -> 2
ROW_STEP = [PLACE_6[i] - PLACE_1[i] for i in range(3)]   # (dx, dy, dz) 1 -> 6

# Per-slot fine correction (dx, dy, dz) in mm, checked on the real cell
#   #4  was ~4 mm too close at +0, then 2-4 mm too far at +4 -> +1
#   #10 was ~8 mm too close at +0, then 2-4 mm too far at +8 -> +4
SLOT_CORRECTION = {
    4: (0.0, 1.0, 0.0),
    10: (0.0, 4.0, 0.0),
}

# Placement order: first #2, then repeat for #4, #8, #10
PLACE_SEQUENCE = [2, 4, 8, 10]


# ==============================================================================
# PALLET MAP (1-25 -> (approach, place))
# ==============================================================================
def build_pallet_map() -> Dict[int, List[float]]:
    """Slot n place pose = place-1 + col * COL_STEP + row * ROW_STEP (place-1 orientation)."""
    pallet = {}
    for n in range(1, PALLET_COLS * PALLET_ROWS + 1):
        row, col = divmod(n - 1, PALLET_COLS)
        fix = SLOT_CORRECTION.get(n, (0.0, 0.0, 0.0))
        xyz = [PLACE_1[i] + col * COL_STEP[i] + row * ROW_STEP[i] + fix[i] for i in range(3)]
        pallet[n] = [*xyz, *PLACE_1[3:]]
    return pallet


PALLET = build_pallet_map()


def approach_of(pose: List[float], dist: float = APPROACH_DIST) -> List[float]:
    """Back off `dist` mm along the tool -Z axis (straight in / out, even when tilted)."""
    u, v, w = (math.radians(a) for a in pose[3:6])
    cu, su = math.cos(u), math.sin(u)
    cv, sv = math.cos(v), math.sin(v)
    cw, sw = math.cos(w), math.sin(w)
    # tool Z axis in base frame: column 3 of Rz(w) * Ry(v) * Rx(u)
    zx = cw * sv * cu + sw * su
    zy = sw * sv * cu - cw * su
    zz = cv * cu
    return [pose[0] - dist * zx, pose[1] - dist * zy, pose[2] - dist * zz, *pose[3:6]]


def fmt(pose: List[float]) -> str:
    return "[" + ", ".join(f"{v:8.2f}" for v in pose) + "]"


# ==============================================================================
# MOTION / IO HELPERS
# ==============================================================================
class MotionError(RuntimeError):
    pass


def wait_move_done(indy: IndyDCP3, timeout: float = MOVE_TIMEOUT) -> None:
    """Block until motion finishes and controller is IDLE; raise on fault/timeout."""
    start = time.time()

    while time.time() - start < 0.5:
        if indy.get_motion_data().get("is_in_motion", False):
            break
        time.sleep(0.02)

    while time.time() - start < timeout:
        m_data = indy.get_motion_data()
        op_state = indy.get_robot_data().get("op_state")

        if op_state in (OpState.VIOLATE, OpState.VIOLATE_HARD,
                        OpState.COLLISION, OpState.STOP_AND_OFF):
            raise MotionError(f"Robot fault during motion (op_state={op_state})")

        if not m_data.get("is_in_motion", False) and op_state == OpState.IDLE:
            print("\r    progress [100%]")
            return

        print(f"\r    progress [{m_data.get('traj_progress', 0):>3}%]", end="", flush=True)
        time.sleep(0.05)

    raise MotionError("Motion timeout")


def check(result, name: str) -> None:
    if isinstance(result, dict) and result.get("code") not in (0, "0", None):
        raise MotionError(f"{name} rejected: {result}")


def move_home(indy: IndyDCP3) -> None:
    print("\n[HOME] move_home()")
    check(indy.move_home(), "move_home")
    wait_move_done(indy)


def move_j(indy: IndyDCP3, q: List[float], label: str,
           vel: int = TRANSIT_VEL, acc: int = TRANSIT_ACC) -> None:
    print(f"  {label:<26} J{fmt(q)}")
    check(indy.movej(jtarget=list(q), base_type=JointBaseType.ABSOLUTE,
                     vel_ratio=vel, acc_ratio=acc), label)
    wait_move_done(indy)


def move_j_to_pose(indy: IndyDCP3, pose: List[float], seed_q: List[float], label: str) -> None:
    """MoveJ to a task pose: IK seeded with a taught joint pose keeps the same arm config."""
    res = indy.inverse_kin(tpos=list(pose), init_jpos=list(seed_q))
    q = res.get("jpos") if isinstance(res, dict) else None
    if not q or len(q) != 6:
        raise MotionError(f"IK failed for {label} {fmt(pose)}: {res}")
    if max(abs(a - b) for a, b in zip(q, seed_q)) > 60.0:
        raise MotionError(f"IK for {label} jumped to another arm config: {fmt(q)}")
    move_j(indy, q, label)


def move_l(indy: IndyDCP3, pose: List[float], label: str,
           vel: int = ACTION_VEL, acc: int = ACTION_ACC) -> None:
    print(f"  {label:<26} L{fmt(pose)}")
    check(indy.movel(ttarget=list(pose), base_type=TaskBaseType.ABSOLUTE,
                     vel_ratio=vel, acc_ratio=acc), label)
    wait_move_done(indy)


def vacuum(indy: IndyDCP3, on: bool, dwell: float = VACUUM_DWELL) -> None:
    print(f"  VACUUM {'ON ' if on else 'OFF'} (DO{VACUUM_DO})")
    check(indy.set_do([{"address": VACUUM_DO, "state": 1 if on else 0}]), "set_do")
    time.sleep(dwell)


# ==============================================================================
# PICK & PLACE CYCLE
# ==============================================================================
def pick_and_place(indy: IndyDCP3, slot: int) -> None:
    place = PALLET[slot]
    place_app = approach_of(place)
    feed_app = approach_of(PICK_FEED)
    feed_near = approach_of(PICK_FEED, FEED_CREEP_DIST)   # same line, creep distance out

    # 2) feeder pick approach (joint move, pick-feed arm config)
    move_j_to_pose(indy, feed_app, PICK_FEED_Q, "2) pick approach (J)")
    # 3) pick location: fast down the tool axis, then creep the last few mm
    move_l(indy, feed_near, "3) pick near")
    move_l(indy, PICK_FEED, "3) pick location (creep)", FEED_CREEP_VEL, FEED_CREEP_ACC)
    # 3-1) vacuum on at magazine point, wait for a full seal
    vacuum(indy, True, PICK_VACUUM_DWELL)
    # 4) pick retract: creep the first few mm out, then normal speed
    move_l(indy, feed_near, "4) pick lift (creep)", FEED_CREEP_VEL, FEED_CREEP_ACC)
    move_l(indy, feed_app, "4) pick retract")
    # 5) pallet place approach (joint move, place-1 arm config)
    move_j_to_pose(indy, place_app, PLACE_1_Q, f"5) place approach #{slot} (J)")
    # 6) place location
    move_l(indy, place, f"6) place location #{slot}")
    # 7) vacuum off
    vacuum(indy, False)
    # retract straight up before the next transit
    move_l(indy, place_app, "   place retract")


def run(indy: IndyDCP3) -> None:
    r = indy.get_robot_data()
    print(f"Connected. op_state={r.get('op_state')}  p={fmt(r.get('p', []))}")
    if r.get("op_state") != OpState.IDLE:
        raise MotionError(f"Robot not IDLE (op_state={r.get('op_state')}). "
                          "Recover / servo-on from the teach pendant first.")

    vacuum(indy, False)            # start with suction released
    move_home(indy)                # 1) home

    for i, slot in enumerate(PLACE_SEQUENCE, start=1):
        print(f"\n===== Cycle {i}/{len(PLACE_SEQUENCE)} : feeder -> pallet #{slot} =====")
        pick_and_place(indy, slot)

    move_home(indy)
    print("\n[DONE] Placed on pallet slots:", PLACE_SEQUENCE)


def safe_stop(indy: IndyDCP3) -> None:
    print("\n[SAFE STOP] stopping motion & releasing vacuum")
    for fn in (lambda: indy.stop_motion(),
               lambda: indy.set_do([{"address": VACUUM_DO, "state": 0}])):
        try:
            fn()
        except Exception as e:
            print("  ->", e)


# ==============================================================================
# ENTRY
# ==============================================================================
def dry_run() -> None:
    print("PICK-FEED        ", fmt(PICK_FEED))
    print("PICK-FEED approach", fmt(approach_of(PICK_FEED)))
    print(f"COL step (1->2)  {fmt(COL_STEP)}  |{math.dist(PLACE_1[:3], PLACE_2[:3]):.2f} mm|")
    print(f"ROW step (1->6)  {fmt(ROW_STEP)}  |{math.dist(PLACE_1[:3], PLACE_6[:3]):.2f} mm|")
    print("\nPallet map (place / approach xyz):")
    for n, pose in PALLET.items():
        mark = "  <-- place" if n in PLACE_SEQUENCE else ""
        print(f"  #{n:<2} {fmt(pose)}  app {fmt(approach_of(pose)[:3])}{mark}")


def teach() -> None:
    indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    r = indy.get_robot_data()
    print("q (deg):", [round(v, 2) for v in r.get("q", [])])
    print("p      :", [round(v, 3) for v in r.get("p", [])])


def main() -> int:
    if "--dry-run" in sys.argv:
        dry_run()
        return 0
    if "--teach" in sys.argv:
        teach()
        return 0

    dry_run()
    input(f"\nRobot {ROBOT_IP}: keep clear of the cell, hand on E-stop. ENTER to start...")

    indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    try:
        run(indy)
        return 0
    except KeyboardInterrupt:
        print("\n[ABORT] user interrupt")
        safe_stop(indy)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        safe_stop(indy)
    return 1


if __name__ == "__main__":
    sys.exit(main())
