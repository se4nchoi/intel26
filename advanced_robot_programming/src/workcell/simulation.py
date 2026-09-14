import threading
import time

from workcell.models import CellError, Detection, Interlocks, Pose


class Scenario:
    """Explicit, shared simulated world. Mutated only through simulation controls."""

    def __init__(self, delay: float = 0.12):
        self.lock = threading.Lock()
        self.delay = delay
        self.part = "red_cube"
        self.fault = "none"
        self.request_id = 0
        self.estop = False
        self.permit = True

    def configure(self, **values):
        with self.lock:
            for key, value in values.items():
                setattr(self, key, value)

    def values(self):
        with self.lock:
            return {k: getattr(self, k) for k in ("part", "fault", "request_id", "estop", "permit")}


class SimRobot:
    def __init__(self, scenario: Scenario, pose: Pose):
        self.world = scenario
        self.pose = pose
        self.connected = False
        self.closed = False
        self.stops = 0
        self.moves = []

    def connect(self):
        self.connected = True

    def status(self):
        if not self.connected or self.world.values()["fault"] == "robot_disconnect":
            raise CellError("Simulated robot disconnected")
        return {
            "connected": True,
            "source": "simulation",
            "pose": self.pose.values,
            "gripper_closed": self.closed,
            "op_state": "IDLE",
        }

    def _wait(self, guard):
        end = time.monotonic() + self.world.delay
        while True:
            guard()
            self.status()
            if time.monotonic() >= end:
                return
            time.sleep(0.01)

    def move(self, pose, guard):
        self._wait(guard)
        if self.world.values()["fault"] == "motion_failure":
            raise CellError("Simulated motion failed to reach its target")
        self.moves.append(pose)
        self.pose = pose

    def grip(self, closed, guard):
        self._wait(guard)
        self.closed = closed

    def verify_grip(self, closed, guard):
        self._wait(guard)
        fault = self.world.values()["fault"]
        if (closed and fault == "grip_failure") or (not closed and fault == "release_failure"):
            raise CellError("Simulated gripper feedback did not confirm the requested state")
        if self.closed != closed:
            raise CellError("Gripper feedback mismatch")

    def stop(self):
        self.stops += 1

    def close(self):
        self.connected = False


class SimPLC:
    def __init__(self, world: Scenario):
        self.world = world
        self.outputs = []

    def connect(self):
        pass

    def read(self):
        values = self.world.values()
        if values["fault"] == "plc_disconnect":
            raise CellError("Simulated PLC disconnected")
        return Interlocks(values["permit"], values["estop"], values["request_id"], time.monotonic())

    def publish(self, request_id, state, slot):
        self.read()
        self.outputs.append((request_id, str(state), slot))
        self.outputs = self.outputs[-200:]

    def close(self):
        pass


class SimCamera:
    def __init__(self, world: Scenario):
        self.world = world

    def start(self):
        pass

    def inspect(self):
        values = self.world.values()
        if values["fault"] == "camera_disconnect":
            raise CellError("Simulated camera disconnected")
        if values["part"] == "none":
            return None
        age = 10 if values["fault"] == "stale_detection" else 0
        return Detection(values["part"], 0.99, time.monotonic() - age, "simulation", 350)

    def jpeg(self):
        import cv2
        import numpy as np

        if self.world.values()["fault"] == "camera_disconnect":
            raise CellError("Simulated camera disconnected")

        frame = np.full((480, 640, 3), (28, 24, 20), dtype=np.uint8)
        cv2.rectangle(frame, (160, 120), (480, 360), (110, 100, 80), 1)
        part = self.world.values()["part"]
        if part == "red_cube":
            cv2.rectangle(frame, (275, 195), (365, 285), (55, 65, 235), -1)
        elif part == "blue_cylinder":
            cv2.circle(frame, (320, 240), 48, (230, 140, 45), -1)
        cv2.putText(
            frame, "SIMULATED CAMERA", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 200, 210), 1
        )
        ok, data = cv2.imencode(".jpg", frame)
        return data.tobytes() if ok else None

    def close(self):
        pass
