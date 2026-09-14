import time

import pytest
from conftest import command, settle

from workcell.models import CellError, State


def enable(cell):
    result = command(cell, "enable")
    assert result["state"] == State.READY, result


def test_complete_cycle_commits_one_slot_after_release(cell):
    enable(cell)
    result = command(cell, "start")
    assert result["state"] == State.READY
    assert result["slots"][0]["status"] == "OCCUPIED"
    assert len(cell.robot.moves) == 7
    assert cell.store.history()["cycles"][0]["status"] == "COMPLETE"
    assert any(output[1] == "COMPLETE" for output in cell.plc.outputs)


def test_full_pallet_does_not_wrap_or_accept_ninth_cycle(cell):
    enable(cell)
    for _ in range(8):
        result = command(cell, "start")
    assert result["state"] == State.WAITING_FOR_PALLET_CHANGE
    assert [s["status"] for s in result["slots"]] == ["OCCUPIED"] * 8
    with pytest.raises(CellError):
        cell.submit("start")
    assert len(cell.store.history()["cycles"]) == 8


@pytest.mark.parametrize("fault", ["motion_failure", "grip_failure", "release_failure"])
def test_failed_execution_latches_fault_and_marks_reservation_unknown(cell, fault):
    enable(cell)
    cell.scenario.configure(fault=fault)
    result = command(cell, "start")
    assert result["state"] == State.FAULT
    assert not result["enabled"]
    assert result["slots"][0]["status"] == "UNKNOWN"
    assert cell.store.history()["cycles"][0]["status"] == "FAULT"
    assert not any(output[1] == "COMPLETE" for output in cell.plc.outputs)
    assert cell.robot.stops >= 1


@pytest.mark.parametrize(
    "scenario",
    [
        {"part": "none"},
        {"fault": "stale_detection"},
        {"fault": "camera_disconnect"},
    ],
)
def test_bad_inspection_never_allocates_or_moves(cell, scenario):
    enable(cell)
    cell.scenario.configure(**scenario)
    result = command(cell, "start")
    assert result["state"] == State.FAULT
    assert not cell.robot.moves
    assert not cell.store.history()["cycles"]
    assert all(s["status"] == "EMPTY" for s in result["slots"])


def test_blue_part_routes_to_magazine_without_consuming_pallet(cell):
    cell.scenario.configure(part="blue_cylinder")
    enable(cell)
    result = command(cell, "start")
    assert result["state"] == State.READY
    assert all(s["status"] == "EMPTY" for s in result["slots"])
    assert cell.robot.moves[-2].values == cell.settings.recipe.magazine


def test_recovery_requires_reconciliation_and_explicit_reenable(cell):
    enable(cell)
    cell.scenario.configure(fault="grip_failure")
    command(cell, "start")
    cell.scenario.configure(fault="none")
    result = command(cell, "reset", note="Fixture inspected")
    assert result["state"] == State.FAULT
    command(cell, "reconcile", slot=0, occupied=False, note="Slot is empty")
    result = command(cell, "reset", note="Gripper cleared and fixture inspected")
    assert result["state"] == State.DISABLED
    assert not result["enabled"]
    enable(cell)
    assert command(cell, "start")["state"] == State.READY


def test_stop_interrupts_cycle_and_rejects_concurrent_start(cell):
    cell.scenario.delay = 0.2
    enable(cell)
    cell.submit("start")
    deadline = time.monotonic() + 3
    while cell.state != State.PICKING and time.monotonic() < deadline:
        time.sleep(0.005)
    with pytest.raises(CellError):
        cell.submit("start")
    cell.request_stop()
    result = settle(cell)
    assert result["state"] == State.FAULT
    assert not any(output[1] == "COMPLETE" for output in cell.plc.outputs)


def test_plc_permit_loss_during_motion_stops_cycle(cell):
    cell.scenario.delay = 0.2
    enable(cell)
    cell.submit("start")
    deadline = time.monotonic() + 3
    while cell.state != State.PICKING and time.monotonic() < deadline:
        time.sleep(0.005)
    cell.scenario.configure(permit=False)
    assert settle(cell)["state"] == State.FAULT


def test_plc_level_trigger_runs_once_and_requires_zero_then_new_id(cell):
    cell.scenario.configure(request_id=17)
    enable(cell)
    time.sleep(0.25)
    assert not cell.store.history()["cycles"]
    cell.scenario.configure(request_id=0)
    time.sleep(0.25)
    cell.scenario.configure(request_id=18)
    deadline = time.monotonic() + 3
    while not cell.store.history()["cycles"] and time.monotonic() < deadline:
        time.sleep(0.02)
    settle(cell)
    time.sleep(0.3)
    assert len(cell.store.history()["cycles"]) == 1
    assert cell.store.history()["cycles"][0]["request_id"] == 18


def test_pallet_change_requires_disabled_cell(cell):
    enable(cell)
    with pytest.raises(CellError):
        cell.submit("replace_pallet", note="changed")
    command(cell, "start")
    command(cell, "disable")
    command(cell, "replace_pallet", note="Installed empty pallet")
    assert all(s["status"] == "EMPTY" for s in cell.store.slots())
