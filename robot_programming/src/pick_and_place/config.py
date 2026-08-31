"""
Configuration constants for Indy Robot sequences.
"""

ROBOT_IP = "192.168.3.2"
ROBOT_INDEX = 0

# Velocity & Acceleration settings (%)
TRANSIT_VEL_RATIO = 25  # High-speed open-air moves
TRANSIT_ACC_RATIO = 25

ACTION_VEL_RATIO = 15   # Low-speed delicate pick/place moves
ACTION_ACC_RATIO = 15

# Default clearance offset for approach/retract (in mm)
DEFAULT_APPROACH_CLEARANCE = 50.0  # mm above target

# Tool Digital I/O mappings (Controller DO/DI or Tool Flange)
DO_VACUUM_ON = 0        # Digital Output for vacuum solenoid
DO_BLOW_OFF = 1         # Digital Output for blow-off pulse
DO_GRIPPER = 3          # Digital Output for pneumatic/electric jaw gripper (Open/Close)
DI_VACUUM_SENSOR = 0    # Digital Input for vacuum pressure switch
DI_GRIPPER_SENSOR = 3   # Digital Input for gripper sensor / status

# Standard Home Position
HOME_JPOS = [0.0, 0.0, -90.0, 0.0, -90.0, 0.0]
