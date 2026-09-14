"""
Single-Pallet 8-Slot Palletizer & LIFO Depalletizer (Neuromeka IndyDCP3)
========================================================================

Architecture & Control Logic:
-----------------------------
1. PB1 (DI8 / PLC X103) -> Palletize (1 Loop, max 8 items):
   * Iterates i from 0 to 7 using a SINGLE Pallet definition.
   * Floor 0 (Layer 0): items 0..3 (Z = Z_base)
   * Floor 1 (Layer 1): items 4..7 (Z = Z_base + LAYER_HEIGHT)
   * Automatically BREAKS if DI3 (Magazine Sensor) is OFF.
   * Tracks `pallet_count` (number of items currently on the pallet).

2. PB2 (DI9 / PLC X104) -> Smart LIFO Put-Back (De-palletize):
   * Picks items in REVERSE order from the top layer down (e.g., 7 -> 0).
   * Drops each item into MAGAZINE_INSERT_LOCATION (top of feeder).
   * Decrements `pallet_count` after each return until empty.
   * Can be pressed mid-run or when pallet is full.

3. STOP (DI15 / PLC X107 -> Y167) -> Real-time Motion Stop / Abort:
   * Real-time interrupt during any active robot trajectory.
   * Immediately halts robot motion via `stop_motion()` and aborts sequence.
   * Interlocks PB1/PB2 execution while STOP signal is engaged.
"""

import time
import sys
import math
from typing import List, Optional
from neuromeka import IndyDCP3, OpState, TaskBaseType, StopCategory

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
ROBOT_IP = "192.168.3.7"
ROBOT_INDEX = 0

TRANSIT_VEL_RATIO = 45
TRANSIT_ACC_RATIO = 45
ACTION_VEL_RATIO  = 25
ACTION_ACC_RATIO  = 25

APPROACH_CLEARANCE_Z = 100.0  # mm above target for safe approach/retract

# ------------------------------------------------------------------------------
# DIGITAL I/O MAPPINGS
# ------------------------------------------------------------------------------
DI_MAGAZINE_SENSOR = 3   # Magazine part presence sensor (Must be ON to pick)
DI_PB1             = 8   # PLC X103 -> Push Button 1 (Start Palletize Loop)
DI_PB2             = 9   # PLC X104 -> Push Button 2 (Put Back to Feeder)
DI_STOP            = 15  # PLC X107 -> Y167 -> Robot DI15 (Emergency / Process Stop)

DO_GRIPPER_OPEN    = 0   # DO0: Gripper Open solenoid
DO_GRIPPER_CLOSE   = 1   # DO1: Gripper Close solenoid
GRIPPER_DWELL_SEC  = 0.5 # Pneumatic settling time

# ------------------------------------------------------------------------------
# SINGLE 2D PALLET DEFINITION (2 x 2 Grid per Layer)
# ------------------------------------------------------------------------------
GRID_X        = 2       # 2 columns in Y (+Y)
GRID_Y        = 2       # 2 rows in X (-X)
SLOTS_PER_FLOOR = GRID_X * GRID_Y  # 4 slots per floor
TOTAL_MAX_ITEMS = 8     # 2 floors x 4 slots = 8 items

OFFSET_X      = 80.0    # Distance between rows in mm
OFFSET_Y      = 80.0    # Distance between columns in mm
LAYER_HEIGHT  = 30.0    # Z height between Floor 0 and Floor 1

# ------------------------------------------------------------------------------
# CALIBRATED TASK COORDINATES [X, Y, Z (mm), U, V, W (deg)]
# ------------------------------------------------------------------------------
PICK_LOCATION            = [232.49, 514.57, 254.19, -19.52, -179.64, 90.03]
DROP_BASE_LOCATION       = [201.75, 219.29, 304.94, -3.24, -179.44, 90.01]
MAGAZINE_INSERT_LOCATION = [-8.15, 515.98, 343.32, -19.46, -177.65, 90.01]
HOME_JPOS                = [0.0, 0.0, -90.0, 0.0, -90.0, 0.0]


# ==============================================================================
# SINGLE-PALLET COORDINATE CALCULATOR
# ==============================================================================
def get_pallet_slot_pose(index: int) -> List[float]:
    """
    Computes the 3D target pose for item `index` (0 to 7) from a SINGLE pallet:
      - Floor (Layer) = index // 4  (0 for 0..3, 1 for 4..7)
      - Slot on Floor = index % 4
      - Row = slot // 2, Col = slot % 2
    """
    layer = index // SLOTS_PER_FLOOR
    slot_in_layer = index % SLOTS_PER_FLOOR
    row = slot_in_layer // GRID_X
    col = slot_in_layer % GRID_X

    base_x, base_y, base_z = DROP_BASE_LOCATION[0], DROP_BASE_LOCATION[1], DROP_BASE_LOCATION[2]
    rot = DROP_BASE_LOCATION[3:]

    x = base_x - (row * OFFSET_X)
    y = base_y + (col * OFFSET_Y)
    z = base_z + (layer * LAYER_HEIGHT)

    return [x, y, z, *rot]


# ==============================================================================
# DIGITAL I/O & GRIPPER HELPERS (INTERLOCKED)
# ==============================================================================
def read_di(indy: IndyDCP3, pin: int) -> bool:
    try:
        di_raw = indy.get_di()
        signals = di_raw.get("signals", []) if isinstance(di_raw, dict) else di_raw
        for sig in signals:
            if isinstance(sig, dict) and sig.get("address") == pin:
                return sig.get("state") in (1, True, "ON", "STATE_ON")
            elif isinstance(sig, (list, tuple)) and len(sig) >= 2 and sig[0] == pin:
                return sig[1] in (1, True, "ON", "STATE_ON")
    except Exception:
        pass
    return False


def is_stop_requested(indy: IndyDCP3) -> bool:
    """Checks whether the Stop button (PLC X107 -> Y167 -> DI15) is asserted."""
    return read_di(indy, DI_STOP)


def set_do(indy: IndyDCP3, pin: int, state: int):
    try:
        indy.set_do([{"address": pin, "state": int(state)}])
    except Exception:
        try:
            indy.set_do([(pin, bool(state))])
        except Exception:
            pass


def open_gripper(indy: IndyDCP3, wait: bool = True):
    set_do(indy, DO_GRIPPER_CLOSE, 0)
    time.sleep(0.02)
    set_do(indy, DO_GRIPPER_OPEN, 1)
    if wait:
        start_wait = time.time()
        while time.time() - start_wait < GRIPPER_DWELL_SEC:
            if is_stop_requested(indy):
                break
            time.sleep(0.02)


def close_gripper(indy: IndyDCP3, wait: bool = True):
    set_do(indy, DO_GRIPPER_OPEN, 0)
    time.sleep(0.02)
    set_do(indy, DO_GRIPPER_CLOSE, 1)
    if wait:
        start_wait = time.time()
        while time.time() - start_wait < GRIPPER_DWELL_SEC:
            if is_stop_requested(indy):
                break
            time.sleep(0.02)


# ==============================================================================
# ROBOT MOTION CONTROL WITH REAL-TIME SAFETY / INTERRUPT
# ==============================================================================
def wait_move_done(indy: IndyDCP3, timeout: float = 30.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < 0.3:
        if is_stop_requested(indy):
            print(f"\n[STOP] X107 Stop triggered on DI{DI_STOP}! Halting motion...")
            try:
                indy.stop_motion(stop_category=StopCategory.CAT2)
            except Exception as e:
                print(f"[WARN] Failed to send stop_motion: {e}")
            return False

        if indy.get_motion_data().get("is_in_motion", False):
            break
        time.sleep(0.02)

    while time.time() - start_time < timeout:
        # Check Stop button (PLC X107 -> Y167 -> DI15) in real-time
        if is_stop_requested(indy):
            print(f"\n[STOP] X107 Stop triggered on DI{DI_STOP}! Halting robot immediately...")
            try:
                indy.stop_motion(stop_category=StopCategory.CAT2)
            except Exception as e:
                print(f"[WARN] Failed to send stop_motion: {e}")
            return False

        m_data = indy.get_motion_data()
        r_data = indy.get_robot_data()
        op_state = r_data.get("op_state")

        if op_state in [OpState.VIOLATE, OpState.VIOLATE_HARD, OpState.COLLISION, OpState.STOP_AND_OFF]:
            print(f"\n[ALERT] Motion aborted due to emergency/collision state: {op_state}")
            return False

        if not m_data.get("is_in_motion", False) and op_state == OpState.IDLE:
            return True

        time.sleep(0.02)

    print("\n[TIMEOUT] Motion did not complete.")
    return False


def movel_abs(indy: IndyDCP3, pose: List[float], vel_ratio: int = ACTION_VEL_RATIO, acc_ratio: int = ACTION_ACC_RATIO) -> bool:
    if is_stop_requested(indy):
        print(f"\n[STOP] Motion prevented: Stop signal DI{DI_STOP} (PLC X107) is active.")
        return False

    indy.movel(
        ttarget=list(pose),
        base_type=TaskBaseType.ABSOLUTE,
        vel_ratio=vel_ratio,
        acc_ratio=acc_ratio,
    )
    return wait_move_done(indy)


def move_home(indy: IndyDCP3) -> bool:
    if is_stop_requested(indy):
        print(f"\n[STOP] Cannot move home: Stop signal DI{DI_STOP} (PLC X107) is active.")
        return False

    print("  [MOTION] Moving to HOME position...")
    indy.move_home()
    return wait_move_done(indy)


def get_approach_pose(target_pose: List[float], clearance: float = APPROACH_CLEARANCE_Z, indy: Optional[IndyDCP3] = None) -> List[float]:
    """
    Computes the 3D approach/retract pose backed off along the tool's approach angle (TCP Z-axis vector).
    Instead of moving straight up in World Z, this moves collinear with the tool orientation,
    allowing the robot to plunge straight in and retract straight out at the exact approach angle.
    """
    if indy is not None:
        try:
            res = indy.calculate_current_pose_rel(
                current_pos=list(target_pose),
                relative_pos=[0.0, 0.0, -clearance, 0.0, 0.0, 0.0],
                base_type=TaskBaseType.TCP,
            )
            if isinstance(res, dict) and "calculated_pos" in res:
                return res["calculated_pos"]
        except Exception:
            pass

    # Direct kinematic projection along tool Z vector:
    # Tool Z vector in base frame: R[:, 2] from R = Rz(w) * Ry(v) * Rx(u)
    u = math.radians(target_pose[3])
    v = math.radians(target_pose[4])
    w = math.radians(target_pose[5])

    cu, su = math.cos(u), math.sin(u)
    cv, sv = math.cos(v), math.sin(v)
    cw, sw = math.cos(w), math.sin(w)

    zx = cw * sv * cu + sw * su
    zy = sw * sv * cu - cw * su
    zz = cv * cu

    # Retract is along -Z_tool direction
    app_x = target_pose[0] - clearance * zx
    app_y = target_pose[1] - clearance * zy
    app_z = target_pose[2] - clearance * zz

    return [app_x, app_y, app_z, target_pose[3], target_pose[4], target_pose[5]]


# ==============================================================================
# 1. PALLETIZE SEQUENCE (PB1: Magazine Feeder -> Pallet, 1 Loop max 8)
# ==============================================================================
def run_palletize_sequence(indy: IndyDCP3, current_count: int) -> int:
    """
    Executes a single for-loop from `current_count` up to 8.
    Breaks immediately if DI3 (Magazine Sensor) is OFF or DI15 (X107 Stop) is ON.
    Returns the updated count of placed items.
    """
    print("\n=======================================================")
    print(f"  [PB1 PALLETIZE] Starting run from Slot {current_count + 1} (Max 8)")
    print("=======================================================")

    count = current_count
    pick_approach = get_approach_pose(PICK_LOCATION, indy=indy)

    for i in range(current_count, TOTAL_MAX_ITEMS):
        # 1. Check Stop Button (PLC X107 -> DI15)
        if is_stop_requested(indy):
            print(f"\n[STOP] X107 Stop active on DI{DI_STOP}. Palletizing aborted.")
            print(f"[STATUS] Pallet items currently placed: {count}/8")
            break

        # 2. Check Magazine Sensor (DI3) -> Break if OFF
        if not read_di(indy, DI_MAGAZINE_SENSOR):
            print(f"\n[STOP] Magazine sensor DI{DI_MAGAZINE_SENSOR} is OFF (Empty).")
            print(f"[STATUS] Palletizing paused. {count} item(s) currently on pallet.")
            break

        slot_pose = get_pallet_slot_pose(i)
        drop_approach = get_approach_pose(slot_pose, indy=indy)
        floor = i // SLOTS_PER_FLOOR

        print(f"\n--- Item {i + 1}/{TOTAL_MAX_ITEMS} [Floor {floor}, Slot {i % 4 + 1}] ---")
        print(f"  Target: X={slot_pose[0]:.2f}, Y={slot_pose[1]:.2f}, Z={slot_pose[2]:.2f}")

        # Pick from Magazine
        open_gripper(indy, wait=False)
        if not movel_abs(indy, pick_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
            break
        if not movel_abs(indy, PICK_LOCATION, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break
        close_gripper(indy, wait=True)
        if not movel_abs(indy, pick_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break

        # Place into Pallet Slot i
        if not movel_abs(indy, drop_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
            break
        if not movel_abs(indy, slot_pose, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break
        open_gripper(indy, wait=True)
        if not movel_abs(indy, drop_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break

        count += 1
        print(f"  [SUCCESS] Item {i + 1} placed cleanly! (Total on pallet: {count})")

    if count == TOTAL_MAX_ITEMS and not is_stop_requested(indy):
        print("\n=======================================================")
        print("  [COMPLETE] All 8 Pallet Slots Filled!")
        print("=======================================================")
        move_home(indy)

    return count


# ==============================================================================
# 2. SMART PUT-BACK SEQUENCE (PB2: Pallet -> Top of Magazine Feeder, LIFO)
# ==============================================================================
def run_put_back_sequence(indy: IndyDCP3, current_count: int) -> int:
    """
    Executes LIFO De-palletizing (from top layer down: count-1 down to 0).
    Drops each item at MAGAZINE_INSERT_LOCATION.
    Breaks immediately if DI15 (X107 Stop) is ON.
    Returns the remaining count of items on pallet (0 when done).
    """
    if current_count == 0:
        print("\n[INFO] Pallet is already empty! No items to return.")
        return 0

    print("\n=======================================================")
    print(f"  [PB2 PUT-BACK] Returning {current_count} item(s) LIFO -> Magazine Feeder")
    print("=======================================================")

    mag_insert_approach = get_approach_pose(MAGAZINE_INSERT_LOCATION, indy=indy)
    count = current_count

    # Iterate in reverse order from top-most placed item down to 0
    for i in range(current_count - 1, -1, -1):
        if is_stop_requested(indy):
            print(f"\n[STOP] X107 Stop active on DI{DI_STOP}. Put-back aborted.")
            print(f"[STATUS] Pallet items remaining: {count}/8")
            break

        slot_pose = get_pallet_slot_pose(i)
        slot_approach = get_approach_pose(slot_pose, indy=indy)
        floor = i // SLOTS_PER_FLOOR

        print(f"\n--- Returning Item {i + 1} [Floor {floor}, Slot {i % 4 + 1}] -> Feeder Top ---")

        # Pick from Pallet Slot
        open_gripper(indy, wait=False)
        if not movel_abs(indy, slot_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
            break
        if not movel_abs(indy, slot_pose, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break
        close_gripper(indy, wait=True)
        if not movel_abs(indy, slot_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break

        # Drop into Magazine Insert Location
        if not movel_abs(indy, mag_insert_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
            break
        if not movel_abs(indy, MAGAZINE_INSERT_LOCATION, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break
        open_gripper(indy, wait=True)
        if not movel_abs(indy, mag_insert_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
            break

        count -= 1
        print(f"  [RETURNED] Item {i + 1} inserted back into feeder! (Remaining on pallet: {count})")

    if count == 0 and not is_stop_requested(indy):
        print("\n=======================================================")
        print("  [COMPLETE] Put-back cycle finished! Returning to HOME.")
        print("=======================================================")
        move_home(indy)

    return count


# ==============================================================================
# MAIN PLC EVENT LISTENER LOOP
# ==============================================================================
def run_plc_listener(indy: IndyDCP3):
    print("\n" + "=" * 65)
    print("     SINGLE-PALLET 8-SLOT & SMART PUT-BACK CONTROLLER")
    print("=" * 65)
    print(f"  * PB1  (PLC X103 -> DI{DI_PB1})         : Palletize Loop (Max 8, breaks if DI3=OFF)")
    print(f"  * PB2  (PLC X104 -> DI{DI_PB2})         : Smart Put-Back (LIFO -> Top of Feeder)")
    print(f"  * STOP (PLC X107 -> Y167 -> DI{DI_STOP}): Emergency / Real-time Motion Stop")
    print(f"  * Magazine Sensor (DI{DI_MAGAZINE_SENSOR})       : Workpiece Sensor")
    print(f"  * Gripper DOs                 : DO{DO_GRIPPER_OPEN}(Open) / DO{DO_GRIPPER_CLOSE}(Close)")
    print("=" * 65)

    if not is_stop_requested(indy):
        move_home(indy)
    else:
        print(f"\n[WARN] DI{DI_STOP} is active on startup. Skipping initial move_home.")

    pallet_count = 0  # Memory: tracks active items on pallet
    last_pb1_state = False
    last_pb2_state = False
    last_stop_state = False
    last_status_time = 0.0

    while True:
        try:
            cur_pb1 = read_di(indy, DI_PB1)
            cur_pb2 = read_di(indy, DI_PB2)
            cur_stop = is_stop_requested(indy)
            cur_mag = read_di(indy, DI_MAGAZINE_SENSOR)

            now = time.time()
            if now - last_status_time > 1.5:
                status_mag = "\033[92mON (Part Present)\033[0m" if cur_mag else "\033[93mOFF (Empty)\033[0m"
                status_pb1 = "\033[96mON\033[0m" if cur_pb1 else "OFF"
                status_pb2 = "\033[96mON\033[0m" if cur_pb2 else "OFF"
                status_stop = "\033[91mON (STOPPED)\033[0m" if cur_stop else "OFF"
                print(f"\r[STATUS] DI3(Mag): {status_mag} | PB1: {status_pb1} | PB2: {status_pb2} | STOP(X107): {status_stop} | Pallet: [{pallet_count}/8]", end="", flush=True)
                last_status_time = now

            # -------------------------------------------------------------
            # Rising Edge: STOP Button Pressed
            # -------------------------------------------------------------
            if cur_stop and not last_stop_state:
                print(f"\n\n>>> [ALERT] STOP Button Pressed (PLC X107 / DI{DI_STOP})! Halting motion...")
                try:
                    indy.stop_motion(stop_category=StopCategory.CAT2)
                except Exception as e:
                    print(f"[WARN] Failed to send stop_motion: {e}")
                last_status_time = 0.0

            # -------------------------------------------------------------
            # Rising Edge: PB1 -> Palletize (1 Loop, max 8)
            # -------------------------------------------------------------
            if cur_pb1 and not last_pb1_state:
                if cur_stop:
                    print(f"\n\n[BLOCKED] Cannot start Palletize: STOP button (PLC X107 / DI{DI_STOP}) is ACTIVE!")
                else:
                    print(f"\n\n>>> [TRIGGER] PB1 Pressed! Starting Palletize Sequence...")
                    pallet_count = run_palletize_sequence(indy, current_count=pallet_count)
                    print(f"\n[READY] Returned to listener. Items on pallet: {pallet_count}/8")
                last_status_time = 0.0

            # -------------------------------------------------------------
            # Rising Edge: PB2 -> Smart Put-Back (LIFO to Feeder)
            # -------------------------------------------------------------
            if cur_pb2 and not last_pb2_state:
                if cur_stop:
                    print(f"\n\n[BLOCKED] Cannot start Put-Back: STOP button (PLC X107 / DI{DI_STOP}) is ACTIVE!")
                else:
                    print(f"\n\n>>> [TRIGGER] PB2 Pressed! Starting Put-Back Sequence...")
                    pallet_count = run_put_back_sequence(indy, current_count=pallet_count)
                    print(f"\n[READY] Returned to listener. Items on pallet: {pallet_count}/8")
                last_status_time = 0.0

            last_pb1_state = cur_pb1
            last_pb2_state = cur_pb2
            last_stop_state = cur_stop
            time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n\n[INFO] User requested stop. Exiting safely.")
            break
        except Exception as e:
            print(f"\n[ERROR] Exception in loop: {e}")
            time.sleep(0.5)


def main():
    print(f"Connecting to Indy Robot at {ROBOT_IP}...")
    try:
        indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
        r_data = indy.get_robot_data()
        print(f"Connected successfully! OpState: {r_data.get('op_state')}")
    except Exception as e:
        print(f"[FATAL] Failed to connect: {e}")
        sys.exit(1)

    run_plc_listener(indy)


if __name__ == "__main__":
    main()

