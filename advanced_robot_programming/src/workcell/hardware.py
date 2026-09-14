"""Hardware adapters. SDK imports and connections happen only on explicit startup."""

import time
from functools import wraps

from workcell.config import PLCConfig, RobotConfig, Workspace
from workcell.models import CellError, Interlocks, Pose, State


class DeadlineStub:
    """Supply gRPC deadlines to calls made by the installed IndyDCP3 SDK."""

    def __init__(self, stub, timeout):
        self.stub, self.timeout = stub, timeout

    def __getattr__(self, name):
        call = getattr(self.stub, name)

        @wraps(call)
        def bounded(*args, **kwargs):
            kwargs.setdefault("timeout", self.timeout)
            return call(*args, **kwargs)

        return bounded


def check_response(result: dict, operation: str):
    response = result.get("response", result) if isinstance(result, dict) else {}
    if response.get("code") != 0:
        raise CellError(f"{operation} rejected or returned an invalid response: {result}")


class IndyRobot:
    def __init__(self, config: RobotConfig, workspace: Workspace, motion_enabled: bool):
        self.config, self.workspace = config, workspace
        self.motion_enabled = motion_enabled
        self.sdk = None

    def connect(self):
        from neuromeka import IndyDCP3

        self.sdk = IndyDCP3(robot_ip=self.config.host, index=self.config.index)
        for name in ("boot", "control", "device", "config", "rtde", "cri"):
            setattr(
                self.sdk, name, DeadlineStub(getattr(self.sdk, name), self.config.rpc_timeout_s)
            )
        self.status()

    def status(self):
        if self.sdk is None:
            raise CellError("Robot is not connected")
        data = self.sdk.get_control_data()
        check_response(data, "Robot telemetry")
        if not data.get("is_robot_connected"):
            raise CellError("Controller reports robot disconnected")
        pose = Pose(tuple(data.get("p", ())))
        return {
            "connected": True,
            "source": "hardware",
            "pose": pose.values,
            "joints": data.get("q"),
            "op_state": data.get("op_state"),
            "controller_simulation": data.get("sim_mode", True),
        }

    def _permission(self):
        if not self.motion_enabled:
            raise CellError("Observation mode cannot command robot motion or outputs")

    def move(self, pose, guard):
        from neuromeka.enums import OpState

        self._permission()
        guard()
        self.workspace.check(pose)
        status = self.status()
        if status["op_state"] != OpState.IDLE or status["controller_simulation"]:
            raise CellError("Physical robot must be idle and outside controller simulation mode")
        self.workspace.check(Pose(tuple(status["pose"])))
        result = self.sdk.movel(
            ttarget=list(pose.values),
            vel_ratio=self.config.velocity_percent,
            acc_ratio=self.config.acceleration_percent,
        )
        check_response(result, "Linear motion")
        end = time.monotonic() + self.config.motion_timeout_s
        stable = 0
        while time.monotonic() < end:
            guard()
            status = self.status()
            if status["op_state"] not in (OpState.IDLE, OpState.MOVING):
                raise CellError(f"Robot entered operation state {status['op_state']}")
            motion = self.sdk.get_motion_data()
            check_response(motion, "Motion telemetry")
            if motion.get("is_stopping") or motion.get("is_pausing"):
                raise CellError("Robot motion was stopped or paused")
            position_ok = all(
                abs(a - b) <= self.config.position_tolerance_mm
                for a, b in zip(status["pose"][:3], pose.values[:3])
            )
            angle_ok = all(
                abs((a - b + 180) % 360 - 180) <= self.config.angle_tolerance_deg
                for a, b in zip(status["pose"][3:], pose.values[3:])
            )
            complete = (
                position_ok
                and angle_ok
                and motion.get("is_target_reached")
                and motion.get("is_in_motion") is False
                and motion.get("motion_queue_size") == 0
                and status["op_state"] == OpState.IDLE
            )
            stable = stable + 1 if complete else 0
            if stable >= 3:
                return
            time.sleep(0.05)
        raise CellError("Robot motion timed out before verified target arrival")

    def grip(self, closed, guard):
        self._permission()
        guard()
        state = closed == self.config.close_do_active_high
        result = self.sdk.set_do([{"address": self.config.close_do, "state": state}])
        check_response(result, "Gripper output")

    def verify_grip(self, closed, guard):
        from neuromeka.enums import DigitalState

        self._permission()
        end = time.monotonic() + self.config.gripper_timeout_s
        stable = 0
        while time.monotonic() < end:
            guard()
            data = self.sdk.get_di()
            if "response" in data:
                check_response(data, "Gripper feedback")
            signals = {s["address"]: s["state"] for s in data.get("signals", [])}
            expected = self.config.closed_di if closed else self.config.open_di
            opposite = self.config.open_di if closed else self.config.closed_di
            active = DigitalState.ON if self.config.feedback_active_high else DigitalState.OFF
            inactive = DigitalState.OFF if self.config.feedback_active_high else DigitalState.ON
            valid = signals.get(expected) == active and signals.get(opposite) == inactive
            valid = valid and signals.get(self.config.part_present_di) == (
                active if closed else inactive
            )
            stable = stable + 1 if valid else 0
            if stable >= 3:
                return
            time.sleep(0.05)
        raise CellError("Gripper feedback timeout: check part, pressure, and input wiring")

    def stop(self):
        # Observation mode is strictly read-only, including shutdown.
        if self.sdk is not None and self.motion_enabled:
            check_response(self.sdk.stop_motion(), "Controlled stop")

    def close(self):
        if self.sdk is not None:
            for name in ("boot", "control", "device", "config", "rtde", "cri"):
                getattr(self.sdk, name + "_channel").close()
            self.sdk = None


STATE_CODES = {state: index for index, state in enumerate(State)}


class MCPLC:
    """Fixed version-1 handshake described in docs/plc-contract.md."""

    def __init__(self, config: PLCConfig, writable: bool):
        self.config, self.writable = config, writable
        self.client = None
        self._heartbeat = None
        self._changed_at = None
        self._seen_change = False
        self._pc_heartbeat = 0
        self._done_id = 0

    def connect(self):
        import pymcprotocol

        self.client = pymcprotocol.Type3E()
        self.client.setaccessopt(commtype="binary", timer_sec=1)
        self.client.soc_timeout = self.config.timeout_s
        self.client.connect(self.config.host, self.config.port)

    def read(self):
        if self.client is None:
            raise CellError("PLC is not connected")
        try:
            bits = self.client.batchread_bitunits(headdevice="M0", readsize=2)
            words = self.client.batchread_wordunits(headdevice="D100", readsize=3)
        except Exception as exc:
            raise CellError(f"PLC read failed: {exc}") from exc
        if len(bits) != 2 or len(words) != 3 or words[2] != 1:
            raise CellError("PLC contract mismatch: D102 must contain version 1")
        heartbeat, request = words[:2]
        if not 0 <= request <= 32767:
            raise CellError("PLC request ID must be between 0 and 32767")
        now = time.monotonic()
        if heartbeat != self._heartbeat:
            self._seen_change = self._heartbeat is not None
            self._heartbeat, self._changed_at = heartbeat, now
        if now - self._changed_at > self.config.heartbeat_timeout_s:
            raise CellError("PLC heartbeat is stale")
        return Interlocks(bool(bits[0]) and self._seen_change, bool(bits[1]), request, now)

    def publish(self, request_id, state, slot):
        if not self.writable:
            return
        if state == State.COMPLETE and request_id:
            self._done_id = request_id
        self._pc_heartbeat = (self._pc_heartbeat + 1) % 32768
        values = [
            request_id,
            STATE_CODES[state],
            -1 if slot is None else slot,
            self._done_id,
            int(state == State.FAULT),
            self._pc_heartbeat,
        ]
        try:
            self.client.batchwrite_wordunits(headdevice="D110", values=values)
        except Exception as exc:
            raise CellError(f"PLC status write failed: {exc}") from exc

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
