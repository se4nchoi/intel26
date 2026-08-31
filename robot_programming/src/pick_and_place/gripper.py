"""
Gripper and end-effector tool controllers for IndyDCP3.
Supports Vacuum/Suction cup tools and standard Pneumatic/Electric jaw grippers.
"""

import time
from abc import ABC, abstractmethod
from neuromeka import IndyDCP3
from .config import DO_VACUUM_ON, DO_BLOW_OFF, DI_VACUUM_SENSOR


class BaseGripper(ABC):
    @abstractmethod
    def grip(self) -> bool:
        """Actuate gripper to grasp / suck the object."""
        pass

    @abstractmethod
    def release(self) -> bool:
        """Actuate gripper to release / drop the object."""
        pass


class VacuumGripper(BaseGripper):
    """
    Controls an industrial Venturi vacuum ejector with optional blow-off pulse
    and digital vacuum pressure switch confirmation.
    """
    def __init__(
        self,
        indy: IndyDCP3,
        vac_do: int = DO_VACUUM_ON,
        blow_do: int = DO_BLOW_OFF,
        sensor_di: int = DI_VACUUM_SENSOR,
    ):
        self.indy = indy
        self.vac_do = vac_do
        self.blow_do = blow_do
        self.sensor_di = sensor_di

    def grip(self, timeout: float = 2.0, check_sensor: bool = False) -> bool:
        """
        Activates suction solenoid.
        If check_sensor=True, verifies negative pressure switch (DI) before returning.
        """
        print("  [TOOL] Vacuum ON...")
        # Ensure blow-off is OFF, turn ON vacuum
        self.indy.set_do([
            {"address": self.blow_do, "state": 0},
            {"address": self.vac_do,  "state": 1},
        ])

        if not check_sensor:
            time.sleep(0.3)  # Brief settling time
            return True

        # Wait for pressure switch confirmation
        start_time = time.time()
        while time.time() - start_time < timeout:
            di_list = self.indy.get_di()
            is_sealed = any(item.get("address") == self.sensor_di and item.get("state") == 1 for item in di_list)
            if is_sealed:
                print("  [TOOL] Vacuum seal confirmed (-70 kPa).")
                return True
            time.sleep(0.02)

        print("  [WARNING] Vacuum pressure switch not triggered (possible leak or missing part)!")
        return False

    def release(self, blow_duration: float = 0.15) -> bool:
        """
        Deactivates suction and pulses the blow-off air solenoid to release instantly.
        """
        print("  [TOOL] Vacuum OFF & Blow-off pulse...")
        # Turn OFF vacuum, turn ON blow-off pulse
        self.indy.set_do([
            {"address": self.vac_do,  "state": 0},
            {"address": self.blow_do, "state": 1},
        ])
        time.sleep(blow_duration)

        # Turn OFF blow-off
        self.indy.set_do([{"address": self.blow_do, "state": 0}])
        return True


class PneumaticJawGripper(BaseGripper):
    """
    Controls a standard 2-finger pneumatic or electric gripper using a single DO channel.
    """
    def __init__(self, indy: IndyDCP3, grip_do: int = 0, dwell_time: float = 0.5):
        self.indy = indy
        self.grip_do = grip_do
        self.dwell_time = dwell_time

    def grip(self) -> bool:
        print("  [TOOL] Closing jaws...")
        self.indy.set_do([{"address": self.grip_do, "state": 1}])
        time.sleep(self.dwell_time)
        return True

    def release(self) -> bool:
        print("  [TOOL] Opening jaws...")
        self.indy.set_do([{"address": self.grip_do, "state": 0}])
        time.sleep(self.dwell_time)
        return True
