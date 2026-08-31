"""
High-level Pick-and-Place sequence engine for IndyDCP3.
Coordinates approach, plunge, grip/vacuum, retract, transit, and placement.
"""

from typing import List, Optional
from neuromeka import IndyDCP3
from .config import (
    ROBOT_IP,
    ROBOT_INDEX,
    DEFAULT_APPROACH_CLEARANCE,
    TRANSIT_VEL_RATIO,
    TRANSIT_ACC_RATIO,
    ACTION_VEL_RATIO,
    ACTION_ACC_RATIO,
)
from .motion import wait_move_done, move_home_safe, movel_abs
from .gripper import BaseGripper, VacuumGripper, PneumaticJawGripper


class PickAndPlaceSequencer:
    def __init__(self, indy: IndyDCP3, gripper: Optional[BaseGripper] = None):
        self.indy = indy
        self.gripper = gripper or VacuumGripper(indy)
        self.approach_clearance = DEFAULT_APPROACH_CLEARANCE

    def pick(self, target_pose: List[float]) -> bool:
        """
        Executes a vertical pick action at target_pose: [x, y, z, u, v, w]
        1. Fly to approach clearance above target
        2. Plunge down vertically
        3. Grip / Engage suction
        4. Retract vertically
        """
        approach_pose = list(target_pose)
        approach_pose[2] += self.approach_clearance

        print(f"\n--- [ACTION] Pick Sequence @ {target_pose[:3]} ---")

        # 1. Approach above object
        print("  1. Moving to pick approach...")
        movel_abs(self.indy, approach_pose, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO)

        # 2. Plunge to object surface
        print("  2. Plunging to object surface...")
        movel_abs(self.indy, target_pose, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO)

        # 3. Grip / Vacuum ON
        print("  3. Actuating gripper...")
        self.gripper.grip()

        # 4. Retract straight up
        print("  4. Retracting straight up...")
        movel_abs(self.indy, approach_pose, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO)
        return True

    def place(self, target_pose: List[float]) -> bool:
        """
        Executes a vertical place action at target_pose: [x, y, z, u, v, w]
        1. Fly to approach clearance above drop slot
        2. Lower down vertically
        3. Release / Blow-off
        4. Retract vertically
        """
        approach_pose = list(target_pose)
        approach_pose[2] += self.approach_clearance

        print(f"\n--- [ACTION] Place Sequence @ {target_pose[:3]} ---")

        # 1. Approach above destination
        print("  1. Moving to place approach...")
        movel_abs(self.indy, approach_pose, vel_ratio=TRANSIT_VEL_RATIO, acc_ratio=TRANSIT_ACC_RATIO)

        # 2. Lower into position
        print("  2. Lowering into position...")
        movel_abs(self.indy, target_pose, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO)

        # 3. Release / Blow-off
        print("  3. Releasing object...")
        self.gripper.release()

        # 4. Retract straight up
        print("  4. Retracting straight up...")
        movel_abs(self.indy, approach_pose, vel_ratio=ACTION_VEL_RATIO, acc_ratio=ACTION_ACC_RATIO)
        return True

    def run_single_cycle(self, pick_pose: List[float], place_pose: List[float]) -> bool:
        """Executes a complete Home -> Pick -> Place -> Home cycle."""
        print("\n=======================================================")
        print("           Starting Pick & Place Cycle                 ")
        print("=======================================================")

        move_home_safe(self.indy)
        self.pick(pick_pose)
        self.place(place_pose)
        move_home_safe(self.indy)

        print("\n[SUCCESS] Cycle finished cleanly!")
        return True


def main():
    # Connect to the robot
    print(f"Connecting to Indy robot at {ROBOT_IP}...")
    indy = IndyDCP3(robot_ip=ROBOT_IP, index=ROBOT_INDEX)

    # Initialize tool & sequencer
    tool = VacuumGripper(indy)
    sequencer = PickAndPlaceSequencer(indy=indy, gripper=tool)

    # Example test targets (adjust with waypoint_recorder.py or your calibrated positions)
    SAMPLE_PICK  = [350.0, -150.0, 520.0, 180.0, 0.0, 180.0]
    SAMPLE_PLACE = [350.0,  150.0, 520.0, 180.0, 0.0, 180.0]

    sequencer.run_single_cycle(pick_pose=SAMPLE_PICK, place_pose=SAMPLE_PLACE)


if __name__ == "__main__":
    main()
