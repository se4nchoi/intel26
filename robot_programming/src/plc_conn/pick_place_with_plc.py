"""
PLC-Integrated Pick & Place Sequence for Neuromeka IndyDCP3 Robot
==================================================================

I/O & PLC Mapping:
------------------
  * PLC Input X103 -> Push Button 1 (PB1) -> Robot DI8
  * PLC Input X104 -> Push Button 2 (PB2) -> Robot DI9
  * Workpiece Sensor (Magazine Sensor)    -> Robot DI3
  * Gripper Open Solenoid                 -> Robot DO0 (Interlocked)
  * Gripper Close Solenoid                -> Robot DO1 (Interlocked)

Operational Logic:
------------------
  1. PB1 (DI8) Pressed:
     - Check DI3 (Magazine sensor). If DI3 == OFF, alert and do not start.
     - If DI3 == ON:
       * Open gripper while approaching pick_location.
       * Plunge to pick_location -> Close gripper on target reach.
       * Retract and transit to drop_location approach.
       * Plunge to drop_location -> Open gripper to release.
       * Retract to clearance height.

  2. PB2 (DI9) Pressed (or 2nd stage):
     * Open gripper while approaching drop_location.
     * Plunge to drop_location -> Close gripper to pick up.
     * Retract and transit to magazine_insert_location approach.
     * Plunge to magazine_insert_location -> Open gripper to insert/release.
     * Retract to clearance height and return to safe Home position.
"""

import time
import sys
import math
from typing import List, Optional
from neuromeka import IndyDCP3, OpState, TaskBaseType, JointBaseType

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
ROBOT_IP = "192.168.3.7"
ROBOT_INDEX = 0

# Speeds and Accelerations (%)
TRANSIT_VEL_RATIO = 25   # High-speed open-air moves
TRANSIT_ACC_RATIO = 25
ACTION_VEL_RATIO = 15    # Moderate-speed delicate plunge/insert moves
ACTION_ACC_RATIO = 15

# Vertical approach / retract clearance above target pose (mm)
APPROACH_CLEARANCE_Z = 100.0

# ------------------------------------------------------------------------------
# DIGITAL I/O MAPPINGS
# ------------------------------------------------------------------------------
DI_MAGAZINE_SENSOR = 3   # Magazine part presence sensor (Must be ON to pick)
DI_PB1             = 8   # PLC X103 -> Push Button 1 (Trigger Stage 1)
DI_PB2             = 9   # PLC X104 -> Push Button 2 (Trigger Stage 2)

DO_GRIPPER_OPEN    = 0   # Digital Output channel for gripper OPEN solenoid
DO_GRIPPER_CLOSE   = 1   # Digital Output channel for gripper CLOSE solenoid
GRIPPER_DWELL_SEC  = 0.5 # Settling time for pneumatic actuation

# ------------------------------------------------------------------------------
# CALIBRATED TASK COORDINATES [X (mm), Y (mm), Z (mm), U (deg), V (deg), W (deg)]
# ------------------------------------------------------------------------------
PICK_LOCATION = [232.49, 514.57, 254.19, -19.52, -179.64, 90.03]
DROP_LOCATION = [201.75, 219.29, 304.94, -3.24, -179.44, 90.01]
MAGAZINE_INSERT_LOCATION = [-8.15, 515.98, 343.32, -19.46, -177.65, 90.01]

# Default Home joint configuration [deg]
HOME_JPOS = [0.0, 0.0, -90.0, 0.0, -90.0, 0.0]


# ==============================================================================
# DIGITAL I/O & GRIPPER HELPERS
# ==============================================================================
def read_di(indy: IndyDCP3, pin: int) -> bool:
    """Reads a specific digital input state (0=OFF, 1=ON)."""
    try:
        di_raw = indy.get_di()
        signals = di_raw.get("signals", []) if isinstance(di_raw, dict) else di_raw
        for sig in signals:
            if isinstance(sig, dict) and sig.get("address") == pin:
                return sig.get("state") in (1, True, "ON", "STATE_ON")
            elif isinstance(sig, (list, tuple)) and len(sig) >= 2 and sig[0] == pin:
                return sig[1] in (1, True, "ON", "STATE_ON")
    except Exception as e:
        print(f"[WARN] Error reading DI{pin}: {e}")
    return False


def set_do(indy: IndyDCP3, pin: int, state: int):
    """Sets a specific digital output state."""
    try:
        indy.set_do([{"address": pin, "state": int(state)}])
    except Exception:
        try:
            indy.set_do([(pin, bool(state))])
        except Exception as e:
            print(f"[ERROR] Failed to set DO{pin} -> {state}: {e}")


def open_gripper(indy: IndyDCP3, wait: bool = True):
    """
    Actuates gripper to OPEN state with strict interlocking.
    Ensures Close solenoid (DO1) is completely OFF before activating Open (DO0).
    """
    print("  [GRIPPER] Opening gripper (DO1=OFF -> DO0=ON)...")
    set_do(indy, DO_GRIPPER_CLOSE, 0)
    time.sleep(0.02)  # Safety deadtime to guarantee isolation
    set_do(indy, DO_GRIPPER_OPEN, 1)
    if wait:
        time.sleep(GRIPPER_DWELL_SEC)


def close_gripper(indy: IndyDCP3, wait: bool = True):
    """
    Actuates gripper to CLOSE state with strict interlocking.
    Ensures Open solenoid (DO0) is completely OFF before activating Close (DO1).
    """
    print("  [GRIPPER] Closing gripper (DO0=OFF -> DO1=ON)...")
    set_do(indy, DO_GRIPPER_OPEN, 0)
    time.sleep(0.02)  # Safety deadtime to guarantee isolation
    set_do(indy, DO_GRIPPER_CLOSE, 1)
    if wait:
        time.sleep(GRIPPER_DWELL_SEC)


# ==============================================================================
# ROBOT MOTION CONTROL WITH REAL-TIME SAFETY MONITORING
# ==============================================================================
def wait_move_done(indy: IndyDCP3, timeout: float = 30.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < 0.3:
        if indy.get_motion_data().get("is_in_motion", False):
            break
        time.sleep(0.02)

    while time.time() - start_time < timeout:
        m_data = indy.get_motion_data()
        r_data = indy.get_robot_data()
        op_state = r_data.get("op_state")

        if op_state in [OpState.VIOLATE, OpState.VIOLATE_HARD, OpState.COLLISION, OpState.STOP_AND_OFF]:
            print(f"\n[ALERT] Motion aborted due to emergency/collision state: {op_state}")
            return False

        if not m_data.get("is_in_motion", False) and op_state == OpState.IDLE:
            return True

        time.sleep(0.02)

    print("\n[TIMEOUT] Motion did not complete within the expected window.")
    return False


def movel_abs(indy: IndyDCP3, pose: List[float], vel_ratio: int = ACTION_VEL_RATIO, acc_ratio: int = ACTION_ACC_RATIO) -> bool:
    indy.movel(
        ttarget=list(pose),
        base_type=TaskBaseType.ABSOLUTE,
        vel_ratio=vel_ratio,
        acc_ratio=acc_ratio,
    )
    return wait_move_done(indy)


def move_home(indy: IndyDCP3) -> bool:
    """Returns the robot to the configured Home joint position."""
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
# PICK & PLACE SEQUENCES
# ==============================================================================
def execute_stage_1(indy: IndyDCP3) -> bool:
    """
    STAGE 1 (Triggered by PB1 / DI8):
    1. Check DI3 (Magazine Sensor). If OFF -> Abort with alert.
    2. Open gripper while moving to pick approach.
    3. Move down to PICK_LOCATION.
    4. Close gripper (grip workpiece).
    5. Retract to clearance.
    6. Transit to DROP_LOCATION approach.
    7. Plunge down to DROP_LOCATION.
    8. Open gripper (release workpiece).
    9. Retract to clearance.
    """
    print("\n=======================================================")
    print("  [STAGE 1] Starting: Pick (Magazine) -> Drop Location")
    print("=======================================================")

    # Step 0: Check magazine sensor
    is_mag_present = read_di(indy, DI_MAGAZINE_SENSOR)
    print(f"  [SENSOR] Magazine Sensor (DI{DI_MAGAZINE_SENSOR}): {'ON (Part Detected)' if is_mag_present else 'OFF (Empty!)'}")

    if not is_mag_present:
        print("  [ERROR] Magazine sensor DI3 is OFF! No workpiece found in magazine. Aborting Stage 1.")
        return False

    pick_approach = get_approach_pose(PICK_LOCATION, indy=indy)
    drop_approach = get_approach_pose(DROP_LOCATION, indy=indy)

    # Step 1: Open gripper while approaching pick location
    print("  1. Opening gripper & moving to Pick Approach...")
    open_gripper(indy, wait=False)  # Non-blocking open while robot moves
    if not movel_abs(indy, pick_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
        return False

    # Step 2: Plunge to pick_location
    print(f"  2. Plunging to Pick Location {PICK_LOCATION[:3]}...")
    if not movel_abs(indy, PICK_LOCATION, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 3: Close gripper when reaching target
    print("  3. Target reached. Closing gripper...")
    close_gripper(indy, wait=True)

    # Step 4: Retract vertically
    print("  4. Retracting to clearance height...")
    if not movel_abs(indy, pick_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 5: Transit to drop_location approach
    print(f"  5. Transiting to Drop Approach {drop_approach[:3]}...")
    if not movel_abs(indy, drop_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
        return False

    # Step 6: Lower to drop_location
    print(f"  6. Lowering to Drop Location {DROP_LOCATION[:3]}...")
    if not movel_abs(indy, DROP_LOCATION, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 7: Open gripper to release workpiece
    print("  7. Releasing workpiece at Drop Location...")
    open_gripper(indy, wait=True)

    # Step 8: Retract vertically
    print("  8. Retracting to clearance height...")
    if not movel_abs(indy, drop_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    print("  [SUCCESS] Stage 1 finished successfully!")
    return True


def execute_stage_2(indy: IndyDCP3) -> bool:
    """
    STAGE 2 (Triggered by PB2 / DI9):
    1. Open gripper while moving to drop approach.
    2. Plunge down to DROP_LOCATION.
    3. Close gripper (pick workpiece from drop table).
    4. Retract to clearance.
    5. Transit to MAGAZINE_INSERT_LOCATION approach.
    6. Plunge down to MAGAZINE_INSERT_LOCATION.
    7. Open gripper (insert/release into magazine slot).
    8. Retract to clearance & Return to Home.
    """
    print("\n=======================================================")
    print("  [STAGE 2] Starting: Pick (Drop Pos) -> Magazine Insert")
    print("=======================================================")

    drop_approach = get_approach_pose(DROP_LOCATION, indy=indy)
    mag_insert_approach = get_approach_pose(MAGAZINE_INSERT_LOCATION, indy=indy)

    # Step 1: Open gripper and move to drop approach
    print("  1. Opening gripper & moving to Drop Approach...")
    open_gripper(indy, wait=False)
    if not movel_abs(indy, drop_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
        return False

    # Step 2: Plunge to drop_location
    print(f"  2. Plunging to Drop Location {DROP_LOCATION[:3]}...")
    if not movel_abs(indy, DROP_LOCATION, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 3: Close gripper to pick
    print("  3. Target reached. Closing gripper to grasp workpiece...")
    close_gripper(indy, wait=True)

    # Step 4: Retract vertically
    print("  4. Retracting to clearance height...")
    if not movel_abs(indy, drop_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 5: Transit to magazine insert approach
    print(f"  5. Transiting to Magazine Insert Approach {mag_insert_approach[:3]}...")
    if not movel_abs(indy, mag_insert_approach, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO):
        return False

    # Step 6: Lower to magazine insert location
    print(f"  6. Lowering into Magazine Insert Location {MAGAZINE_INSERT_LOCATION[:3]}...")
    if not movel_abs(indy, MAGAZINE_INSERT_LOCATION, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 7: Open gripper to release inside magazine
    print("  7. Releasing workpiece at Magazine Insert Location...")
    open_gripper(indy, wait=True)

    # Step 8: Retract vertically
    print("  8. Retracting to clearance height...")
    if not movel_abs(indy, mag_insert_approach, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO):
        return False

    # Step 9: Return to Home safe pose
    print("  9. Returning to safe HOME position...")
    move_home(indy)

    print("  [SUCCESS] Stage 2 finished successfully!")
    return True


# ==============================================================================
# MAIN PLC EVENT LISTENER LOOP
# ==============================================================================
def run_plc_listener(indy: IndyDCP3):
    """
    Monitors PLC Push Button inputs (PB1 on DI8, PB2 on DI9) and Magazine sensor (DI3).
    Executes associated pick-and-place stages on rising-edge button presses.
    """
    print("\n" + "=" * 65)
    print("      PLC I/O PICK & PLACE CONTROLLER RUNNING")
    print("=" * 65)
    print(f"  * PB1 Trigger (Stage 1) -> Robot DI{DI_PB1} (PLC X103)")
    print(f"  * PB2 Trigger (Stage 2) -> Robot DI{DI_PB2} (PLC X104)")
    print(f"  * Magazine Sensor       -> Robot DI{DI_MAGAZINE_SENSOR}")
    print(f"  * Gripper Solenoids     -> Robot DO{DO_GRIPPER_OPEN}(Open) / DO{DO_GRIPPER_CLOSE}(Close) [Interlocked]")
    print("=" * 65)
    print("Ready and listening for PLC inputs... (Press Ctrl+C to stop)\n")

    # Move to Home on startup
    move_home(indy)

    last_pb1_state = False
    last_pb2_state = False
    last_status_time = 0.0

    while True:
        try:
            # Poll inputs
            cur_pb1 = read_di(indy, DI_PB1)
            cur_pb2 = read_di(indy, DI_PB2)
            cur_mag = read_di(indy, DI_MAGAZINE_SENSOR)

            now = time.time()
            # Print periodic live status every 1.5 seconds if idle
            if now - last_status_time > 1.5:
                status_mag = "\033[92mON (Part Present)\033[0m" if cur_mag else "\033[93mOFF (Empty)\033[0m"
                status_pb1 = "\033[96mON\033[0m" if cur_pb1 else "OFF"
                status_pb2 = "\033[96mON\033[0m" if cur_pb2 else "OFF"
                print(f"\r[STATUS] DI{DI_MAGAZINE_SENSOR}(Mag): {status_mag} | DI{DI_PB1}(PB1): {status_pb1} | DI{DI_PB2}(PB2): {status_pb2} | Awaiting PB press...", end="", flush=True)
                last_status_time = now

            # -------------------------------------------------------------
            # Rising Edge Detection: PB1 (DI8) -> Trigger Stage 1
            # -------------------------------------------------------------
            if cur_pb1 and not last_pb1_state:
                print(f"\n\n>>> [TRIGGER] PB1 Pressed (DI{DI_PB1}=ON). Initiating Stage 1...")
                execute_stage_1(indy)
                print("\n[READY] Returning to PLC listener mode...")
                last_status_time = 0.0

            # -------------------------------------------------------------
            # Rising Edge Detection: PB2 (DI9) -> Trigger Stage 2
            # -------------------------------------------------------------
            if cur_pb2 and not last_pb2_state:
                print(f"\n\n>>> [TRIGGER] PB2 Pressed (DI{DI_PB2}=ON). Initiating Stage 2...")
                execute_stage_2(indy)
                print("\n[READY] Returning to PLC listener mode...")
                last_status_time = 0.0

            last_pb1_state = cur_pb1
            last_pb2_state = cur_pb2

            # Poll frequency: ~20Hz
            time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n\n[INFO] User requested stop. Exiting PLC listener safely.")
            break
        except Exception as e:
            print(f"\n[ERROR] Exception in PLC loop: {e}")
            time.sleep(0.5)


def main():
    print(f"Connecting to Indy Robot at {ROBOT_IP}...")
    try:
        indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    except Exception as e:
        print(f"[FATAL] Failed to connect to robot at {ROBOT_IP}: {e}")
        sys.exit(1)

    # Initial connection status check
    try:
        r_data = indy.get_robot_data()
        op_state = r_data.get("op_state", "UNKNOWN")
        print(f"Connected successfully! Robot OpState: {op_state}")
        cur_q = [round(x, 2) for x in r_data.get("q", [])]
        print(f"Current Joint Angles (q): {cur_q}")
    except Exception as e:
        print(f"[WARN] Connected, but failed to fetch robot status: {e}")

    # Start PLC listener
    run_plc_listener(indy)


if __name__ == "__main__":
    main()
