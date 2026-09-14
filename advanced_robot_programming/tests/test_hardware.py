import time

import pytest

from workcell.config import PLCConfig, RobotConfig, Workspace
from workcell.hardware import MCPLC, DeadlineStub, IndyRobot, check_response
from workcell.models import CellError, Pose, State


class SDKDouble:
    def __init__(self):
        from neuromeka.enums import OpState

        self.idle = OpState.IDLE
        self.pose = [230, 500, 450, 0, 180, 90]
        self.closed = False
        self.part_present = False
        self.reject = False
        self.reach = True
        self.calls = []

    def get_control_data(self):
        return {
            "response": {"code": 0},
            "p": self.pose,
            "q": [0] * 6,
            "op_state": self.idle,
            "is_robot_connected": True,
            "sim_mode": False,
        }

    def movel(self, *, ttarget, vel_ratio, acc_ratio):
        self.calls.append(("movel", ttarget, vel_ratio, acc_ratio))
        if self.reach:
            self.pose = ttarget
        return {"response": {"code": 7 if self.reject else 0}}

    def get_motion_data(self):
        return {
            "response": {"code": 0},
            "is_target_reached": self.reach,
            "is_in_motion": not self.reach,
            "motion_queue_size": 0,
        }

    def set_do(self, do_signal_list):
        self.calls.append(("set_do", do_signal_list))
        self.closed = do_signal_list[0]["state"]
        self.part_present = self.closed
        return {"response": {"code": 0}}

    def get_di(self):
        from neuromeka.enums import DigitalState

        return {
            "signals": [
                {"address": address, "state": DigitalState.ON if active else DigitalState.OFF}
                for address, active in enumerate((self.closed, not self.closed, self.part_present))
            ]
        }

    def stop_motion(self):
        self.calls.append(("stop",))
        return {"response": {"code": 0}}


def adapter(**config):
    robot = IndyRobot(RobotConfig(**config), Workspace(), True)
    robot.sdk = SDKDouble()
    return robot


def test_motion_uses_installed_sdk_signature_and_verified_arrival():
    robot = adapter()
    robot.move(Pose((240, 510, 450, 0, -180, 90)), lambda: None)
    assert robot.sdk.calls == [("movel", [240, 510, 450, 0, -180, 90], 5, 10)]


def test_sdk_rejection_cannot_be_mistaken_for_motion_success():
    robot = adapter()
    robot.sdk.reject = True
    with pytest.raises(CellError, match="rejected"):
        robot.move(Pose((240, 510, 450, 0, 180, 90)), lambda: None)


def test_motion_timeout_is_bounded():
    robot = adapter(motion_timeout_s=0.05)
    robot.sdk.reach = False
    start = time.monotonic()
    with pytest.raises(CellError, match="timed out"):
        robot.move(Pose((240, 510, 450, 0, 180, 90)), lambda: None)
    assert time.monotonic() - start < 0.3


def test_gripper_uses_signal_list_and_requires_part_presence():
    robot = adapter(gripper_timeout_s=0.05)
    robot.grip(True, lambda: None)
    assert robot.sdk.calls[-1] == ("set_do", [{"address": 0, "state": True}])
    robot.sdk.part_present = False
    with pytest.raises(CellError, match="feedback timeout"):
        robot.verify_grip(True, lambda: None)


def test_observe_adapter_rejects_all_actuation_and_does_not_stop():
    robot = adapter()
    robot.motion_enabled = False
    with pytest.raises(CellError, match="Observation"):
        robot.move(Pose((240, 510, 450, 0, 180, 90)), lambda: None)
    with pytest.raises(CellError, match="Observation"):
        robot.grip(True, lambda: None)
    robot.stop()
    assert not robot.sdk.calls


def test_deadline_wrapper_injects_rpc_timeout():
    class Stub:
        def GetControlData(self, request, *, timeout):
            return request, timeout

    assert DeadlineStub(Stub(), 0.5).GetControlData("request") == ("request", 0.5)


@pytest.mark.parametrize("response", [{}, {"error": "rejected"}, {"response": {"code": 1}}, None])
def test_missing_or_failed_response_rejected(response):
    with pytest.raises(CellError):
        check_response(response, "test")


class MCDouble:
    def __init__(self):
        self.words = [10, 0, 1]
        self.bits = [1, 0]
        self.writes = []

    def batchread_bitunits(self, *, headdevice, readsize):
        assert (headdevice, readsize) == ("M0", 2)
        return self.bits

    def batchread_wordunits(self, *, headdevice, readsize):
        assert (headdevice, readsize) == ("D100", 3)
        return self.words

    def batchwrite_wordunits(self, *, headdevice, values):
        self.writes.append((headdevice, values))


def plc(writable=True):
    device = MCPLC(PLCConfig(heartbeat_timeout_s=0.02), writable)
    device.client = MCDouble()
    return device


def test_plc_requires_a_changing_heartbeat_and_contract_version():
    device = plc()
    assert not device.read().permit
    device.client.words[0] += 1
    assert device.read().permit
    time.sleep(0.025)
    with pytest.raises(CellError, match="stale"):
        device.read()
    device.client.words[2] = 0
    with pytest.raises(CellError, match="contract mismatch"):
        device.read()


def test_mc_handshake_uses_signed_words_and_persistent_done_id():
    device = plc()
    device.publish(42, State.COMPLETE, None)
    assert device.client.writes[-1][0] == "D110"
    assert device.client.writes[-1][1][2:5] == [-1, 42, 0]
    device.publish(42, State.READY, None)
    assert device.client.writes[-1][1][3] == 42


def test_observe_plc_never_writes():
    device = plc(writable=False)
    device.publish(42, State.COMPLETE, 1)
    assert not device.client.writes


def test_mc_network_failure_is_not_false_estop_clear():
    device = plc()

    def fail(**kwargs):
        raise TimeoutError("lost connection")

    device.client.batchread_bitunits = fail
    with pytest.raises(CellError, match="PLC read failed"):
        device.read()
