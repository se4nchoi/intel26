"""
Interactive Zero-G / Direct Teaching waypoint recorder.
Allows the user to guide the robot by hand and save calibrated poses to a JSON file.
"""

import json
import os
from typing import Dict, List
from neuromeka import IndyDCP3
from .config import ROBOT_IP, ROBOT_INDEX

DEFAULT_WAYPOINTS_FILE = os.path.join(os.path.dirname(__file__), "waypoints.json")


def save_waypoints_file(waypoints: Dict[str, List[float]], filepath: str = DEFAULT_WAYPOINTS_FILE) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(waypoints, f, indent=4)
    print(f"\n[OK] Waypoints saved successfully to: {filepath}")


def load_waypoints_file(filepath: str = DEFAULT_WAYPOINTS_FILE) -> Dict[str, List[float]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Waypoints file not found: {filepath}. Run waypoint_recorder.py first.")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def record_waypoints_interactive(robot_ip: str = ROBOT_IP, output_path: str = DEFAULT_WAYPOINTS_FILE) -> Dict[str, List[float]]:
    """
    Guides the user through an interactive terminal session to teach and record waypoints.
    """
    print(f"Connecting to Indy robot at {robot_ip}...")
    indy = IndyDCP3(robot_ip=robot_ip, index=ROBOT_INDEX)

    waypoints: Dict[str, List[float]] = {}

    print("\n=======================================================")
    print("      IndyDCP3 Interactive Waypoint Recorder           ")
    print("=======================================================")
    print("Enabling Zero-G Direct Teaching Mode (motors compliant)...")
    indy.set_direct_teaching(True)
    print(">> Arm is now free-moving. Guide the arm by hand!\n")

    try:
        # 1. Record Pick Pose
        input("[1/2] Physically move the tool to the PICK pose, then press [ENTER]...")
        pick_pose = indy.get_robot_data().get("p", [])
        waypoints["pick_pose"] = [round(x, 2) for x in pick_pose]
        print(f"  --> Saved 'pick_pose': {waypoints['pick_pose']}")

        # 2. Record Place Pose
        input("\n[2/2] Physically move the tool to the PLACE pose, then press [ENTER]...")
        place_pose = indy.get_robot_data().get("p", [])
        waypoints["place_pose"] = [round(x, 2) for x in place_pose]
        print(f"  --> Saved 'place_pose': {waypoints['place_pose']}")

    finally:
        print("\nDisabling Direct Teaching Mode (locking joints)...")
        indy.set_direct_teaching(False)
        print(">> Joints locked.")

    save_waypoints_file(waypoints, output_path)
    return waypoints


if __name__ == "__main__":
    record_waypoints_interactive()
