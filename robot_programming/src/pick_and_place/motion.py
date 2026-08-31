"""
Motion primitives and synchronization handlers for IndyDCP3.
"""

import time
from typing import List
from neuromeka import IndyDCP3, OpState, TaskBaseType, JointBaseType
from .config import (
    TRANSIT_VEL_RATIO,
    TRANSIT_ACC_RATIO,
    ACTION_VEL_RATIO,
    ACTION_ACC_RATIO,
    HOME_JPOS,
)


def wait_move_done(indy: IndyDCP3, timeout: float = 30.0) -> bool:
    """
    Blocks until the current robot motion is completed and controller settles in IDLE.
    Monitors safety states (collisions, violations, E-stop) and aborts immediately if triggered.
    """
    start_time = time.time()

    # 1. Brief startup check to wait for motion start
    while time.time() - start_time < 0.5:
        if indy.get_motion_data().get("is_in_motion", False):
            break
        time.sleep(0.02)

    # 2. Main wait loop with safety checks
    while time.time() - start_time < timeout:
        m_data = indy.get_motion_data()
        r_data = indy.get_robot_data()
        op_state = r_data.get("op_state")

        # Emergency & Collision Handling
        if op_state in [OpState.VIOLATE, OpState.VIOLATE_HARD, OpState.COLLISION, OpState.STOP_AND_OFF]:
            print(f"\n[ALERT] Motion aborted due to emergency/collision state: {op_state}")
            return False

        # Target reached & settled in IDLE
        if not m_data.get("is_in_motion", False) and op_state == OpState.IDLE:
            print(f"\r  Motion Progress: [100%]", flush=True)
            return True

        prog = m_data.get("traj_progress", 0)
        print(f"\r  Motion Progress: [{prog:>3}%]", end="", flush=True)
        time.sleep(0.05)

    print("\n[TIMEOUT] Motion did not complete within the timeout limit.")
    return False


def move_home_safe(indy: IndyDCP3) -> bool:
    """Commands the robot to return to the default Home position."""
    print(f"\n>>> Moving to HOME position...")
    indy.move_home()
    return wait_move_done(indy)


def movel_abs(indy: IndyDCP3, target_pose: List[float], vel_ratio: int = ACTION_VEL_RATIO, acc_ratio: int = ACTION_ACC_RATIO) -> bool:
    """Linear Cartesian move to an absolute [x, y, z, u, v, w] pose."""
    indy.movel(
        ttarget=list(target_pose),
        base_type=TaskBaseType.ABSOLUTE,
        vel_ratio=vel_ratio,
        acc_ratio=acc_ratio,
    )
    return wait_move_done(indy)


def movel_rel(indy: IndyDCP3, offset: List[float], vel_ratio: int = ACTION_VEL_RATIO, acc_ratio: int = ACTION_ACC_RATIO) -> bool:
    """Linear Cartesian relative move by [dx, dy, dz, du, dv, dw] offset."""
    indy.movel(
        ttarget=list(offset),
        base_type=TaskBaseType.RELATIVE,
        vel_ratio=vel_ratio,
        acc_ratio=acc_ratio,
    )
    return wait_move_done(indy)


def movej_safe(indy: IndyDCP3, target_jpos: List[float], vel_ratio: int = TRANSIT_VEL_RATIO, acc_ratio: int = TRANSIT_ACC_RATIO) -> bool:
    """Joint move to absolute [q1, q2, q3, q4, q5, q6] joint angles."""
    indy.movej(
        jtarget=list(target_jpos),
        base_type=JointBaseType.ABSOLUTE,
        vel_ratio=vel_ratio,
        acc_ratio=acc_ratio,
    )
    return wait_move_done(indy)
