import time
from neuromeka import IndyDCP3, OpState

SAFE_VEL_RATIO = 20
SAFE_ACC_RATIO = 20

def wait_move_done(indy: IndyDCP3, timeout: float):
    start_time = time.time()

    while time.time() - start_time < 0.5:
        m_data = indy.get_motion_data()
        if m_data.get("is_in_motion", False):
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
            print(f"\rMotion Progress: [100%]", flush=True)
            return True

        prog = m_data.get("traj_progress", 0)
        print(f"\rMotion Progress: [{prog:3d}%]", end="", flush=True)
        time.sleep(0.05)

    print("\n[TIMEOUT] Motion not completed within timeout")
    return False

def main():
    ROBOT_IP = "192.168.3.2"

    print(f"Connecting to Indy robot at {ROBOT_IP}...")
    indy = IndyDCP3(robot_ip=ROBOT_IP, index=0)

    WP1 = [0,0,-90,0,-90,0]         # home
    WP2 = [-30,20,-70,30,-80,-50]
    WP3 = [30,10,-60,-20,-70,40]

    indy.move_home()
    wait_move_done(indy, 30.0)
    print(f"Reached Home Position: {[round(x, 2) for x in indy.get_robot_data().get('q', [])]}")
    
    indy.movej(
        jtarget=WP2,
        vel_ratio=SAFE_VEL_RATIO,
        acc_ratio=SAFE_ACC_RATIO
    )

    wait_move_done(indy, 30.0)
    print(f"Reached WP2: {[round(x, 2) for x in indy.get_robot_data().get('q', [])]}")
    
    indy.movej(
        jtarget=WP3,
        vel_ratio=SAFE_VEL_RATIO,
        acc_ratio=SAFE_ACC_RATIO
    )

    wait_move_done(indy, 30.0)
    print(f"Reached WP3: {[round(x, 2) for x in indy.get_robot_data().get('q', [])]}")
    
    indy.move_home()
    wait_move_done(indy, 30.0)
    print(f"Reached Home Position: {[round(x, 2) for x in indy.get_robot_data().get('q', [])]}")

    return 0

if __name__ == "__main__":
    main()

