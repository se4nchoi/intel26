import time
from neuromeka import IndyDCP3, OpState, JointBaseType

SAFE_VEL_RATIO = 20  # Safe speed (25%) for class experiment
SAFE_ACC_RATIO = 20

def wait_for_motion(indy: IndyDCP3, timeout: float = 30.0) -> bool:
    """
    Waits for the robot to complete its current motion.
    Features:
    - Fast startup acknowledgment (no fixed 0.5s sleep lag)
    - Safety state monitoring (aborts immediately on collision/violation)
    - Clean terminal progress reporting
    """
    start_time = time.time()

    # 1. Fast start check: wait briefly for motion to register
    while time.time() - start_time < 0.5:
        m_data = indy.get_motion_data()
        if m_data.get("is_in_motion", False):
            break
        time.sleep(0.02)

    # 2. Main wait loop with safety and completion checks
    while time.time() - start_time < timeout:
        m_data = indy.get_motion_data()
        r_data = indy.get_robot_data()
        op_state = r_data.get("op_state")

        # Abort immediately if robot enters violation or collision state
        if op_state in [OpState.VIOLATE, OpState.VIOLATE_HARD, OpState.COLLISION, OpState.STOP_AND_OFF]:
            print(f"\n[ALERT] Motion aborted due to emergency/collision state: {op_state}")
            return False

        # Success condition: motion completed and controller is settled in IDLE state
        if not m_data.get("is_in_motion", False) and op_state == OpState.IDLE:
            print(f"\r  Motion progress: [100%]", flush=True)
            return True

        # Print live progress
        prog = m_data.get("traj_progress", 0)
        print(f"\r  Motion progress: [{prog:>3}%]", end="", flush=True)
        time.sleep(0.05)

    print("\n[TIMEOUT] Motion did not complete within the timeout limit.")
    return False

def move_to_home(indy: IndyDCP3):
    home_pos = indy.get_home_pos().get("jpos", [0.0, 0.0, -90.0, 0.0, -90.0, 0.0])
    print(f"\n>>> Moving back to HOME position {[round(x, 2) for x in home_pos]} deg...")
    indy.movej(
        jtarget=home_pos,
        vel_ratio=SAFE_VEL_RATIO,
        acc_ratio=SAFE_ACC_RATIO,
    )

    if wait_for_motion(indy):
        cur_q = indy.get_robot_data().get("q", [])
        print(f"\nSuccessfully returned to HOME position! Current q: {[round(x, 2) for x in cur_q]}")
    else:
        print("\nMotion timed out while returning to home position!")
        return


def main():
    ROBOT_IP = "192.168.3.2"
    

    print(f"Connecting to Indy robot at {ROBOT_IP}...")
    indy = IndyDCP3(robot_ip=ROBOT_IP, index=0)

    # initial status
    robot_data = indy.get_robot_data()
    violation_data = indy.get_violation_data()

    print("\n--- Initial Status ---")
    print(f"OpState: {robot_data.get('op_state')}")
    print(f"Current Joint Angles (q): {[round(x, 2) for x in robot_data.get('q', [])]} deg")
    print(f"Current TCP Position (p): {[round(x, 2) for x in robot_data.get('p', [])]}")

    if violation_data.get("violation_code") != "0":
        print(f"Warning: Robot has active violation: {violation_data}")
        return

    move_to_home(indy)

    # move a single joint (+30 deg on Joint 1)
    angle_to_move = 30.0
    target_jpos = indy.get_robot_data().get("q", [])
    target_jpos[0] += angle_to_move
    indy.movej(
        jtarget=target_jpos,
        vel_ratio=SAFE_VEL_RATIO,
        acc_ratio=SAFE_ACC_RATIO,
    )
    
    if wait_for_motion(indy):
        cur_q = indy.get_robot_data().get("q", [])
        print(f"\nSuccessfully reached ZERO position! Current q: {[round(x, 2) for x in cur_q]}")
    else:
        print("\nMotion timed out while moving!")
        return

    # check
    print(">>> after move ")
    robot_data = indy.get_robot_data()
    violation_data = indy.get_violation_data()

    print("\n--- Status After Move ---")
    print(f"OpState: {robot_data.get('op_state')}")
    print(f"Current Joint Angles (q): {[round(x, 2) for x in robot_data.get('q', [])]} deg")
    print(f"Current TCP Position (p): {[round(x, 2) for x in robot_data.get('p', [])]}")
        
    move_to_home(indy)

    # check
    print(">>> after move home ")
    robot_data = indy.get_robot_data()
    violation_data = indy.get_violation_data()

    print("\n--- Status After Move ---")
    print(f"OpState: {robot_data.get('op_state')}")
    print(f"Current Joint Angles (q): {[round(x, 2) for x in robot_data.get('q', [])]} deg")
    print(f"Current TCP Position (p): {[round(x, 2) for x in robot_data.get('p', [])]}")

    return 0

if __name__ == "__main__":
    main()

