"""
Robot Alarm Reset & Recovery Utility for Neuromeka IndyDCP3
============================================================
Use this tool when the robot has triggered an emergency stop, collision,
or violation (Flashing green light / OpState 8).
"""

import time
import sys
from neuromeka import IndyDCP3, OpState

ROBOT_IP = "192.168.3.7"
ROBOT_INDEX = 0

def main():
    print(f"Connecting to Indy Robot at {ROBOT_IP}...")
    try:
        indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)
    except Exception as e:
        print(f"[FATAL] Connection failed: {e}")
        return

    try:
        r_data = indy.get_robot_data()
        op_state = r_data.get("op_state", -1)
        print(f"\nCurrent OpState: {op_state}")
        print(f"Current Joint Angles (q): {[round(x, 2) for x in r_data.get('q', [])]}")
        print(f"Current TCP Position (p): {[round(x, 2) for x in r_data.get('p', [])]}")
    except Exception as e:
        print(f"[WARN] Failed to read robot data: {e}")

    print("\n--- Attempting Recovery Sequence ---")
    
    # 1. Stop any residual motion
    try:
        print("1. Sending StopMotion...")
        indy.stop_motion()
    except Exception as e:
        print(f"   StopMotion response: {e}")

    # 2. Call Recover
    try:
        print("2. Sending Recover command to controller...")
        res = indy.recover()
        print(f"   Recover result: {res}")
    except Exception as e:
        print(f"   Recover failed: {e}")

    time.sleep(1.0)

    # 3. Check status after recover
    try:
        r_data = indy.get_robot_data()
        new_op_state = r_data.get("op_state", -1)
        print(f"\nOpState after recovery: {new_op_state}")
        if new_op_state == 5: # IDLE
            print("\033[92m>>> SUCCESS: Robot is now settled in IDLE (Servo ON). LED should be solid green/blue. <<<\033[0m")
        else:
            print(f"\033[93m>>> Status is OpState={new_op_state}. If still flashing green, please check Conty or hardware E-stop switch. <<<\033[0m")
    except Exception as e:
        print(f"[ERROR] Could not query updated status: {e}")

if __name__ == "__main__":
    main()
