import pytest
from pydantic import ValidationError

from workcell.app import build_controller
from workcell.config import Settings, load_settings
from workcell.models import CellError, Pose
from workcell.storage import Store


def test_crash_recovery_latches_fault_and_preserves_occupied_slots(tmp_path):
    path = str(tmp_path / "cell.db")
    store = Store(path, 8, "a")
    first, slot = store.begin("red_cube", 1, True)
    store.placed(slot)
    store.finish(first)
    store.begin("red_cube", 2, True)
    store.close()
    restored = Store(path, 8, "a")
    try:
        assert restored.slots()[0]["status"] == "OCCUPIED"
        assert restored.slots()[1]["status"] == "UNKNOWN"
        assert restored.get_meta("fault")
        assert restored.history()["cycles"][0]["status"] == "INTERRUPTED"
    finally:
        restored.close()


def test_fault_persists_without_running_cycle(tmp_path):
    path = str(tmp_path / "cell.db")
    store = Store(path, 8, "a")
    store.set_meta("fault", "PLC unavailable")
    store.close()
    store = Store(path, 8, "a")
    assert store.get_meta("fault") == "PLC unavailable"
    store.close()


def test_configuration_cannot_silently_reuse_old_inventory(tmp_path):
    path = str(tmp_path / "cell.db")
    Store(path, 8, "a").close()
    with pytest.raises(CellError, match="different configuration"):
        Store(path, 4, "b")


def test_only_one_process_owner_per_database(tmp_path):
    path = str(tmp_path / "cell.db")
    store = Store(path, 8, "a")
    try:
        with pytest.raises(CellError, match="Another controller"):
            Store(path, 8, "a")
    finally:
        store.close()


@pytest.mark.parametrize(
    "bad",
    [
        {"robot": {"velocity_percent": 50}},
        {"robot": {"closed_di": 0, "open_di": 0}},
        {"workspace": {"z": (600, 100)}},
        {"recipe": {"transfer_z_mm": 200}},
        {"recipe": {"columns": 0}},
        {"vision": {"roi": (600, 0, 200, 200)}},
        {"dry_run": True},
    ],
)
def test_invalid_configuration_is_rejected(bad):
    with pytest.raises((ValidationError, CellError)):
        Settings.model_validate(bad)


def test_invalid_pose_and_out_of_range_slots_rejected():
    with pytest.raises(ValueError):
        Pose((0, 0, float("nan"), 0, 0, 0))
    with pytest.raises(CellError):
        Settings().recipe.slot_pose(8)


def test_checked_in_config_loads():
    from pathlib import Path

    settings = load_settings(Path("config/cell.toml"))
    assert settings.mode == "simulation"
    assert settings.recipe.capacity == 8


@pytest.mark.parametrize(
    "commissioned,reference,allow",
    [
        (False, "", False),
        (True, "record", False),
        (False, "record", True),
        (True, "", True),
    ],
)
def test_automatic_mode_requires_all_gates(commissioned, reference, allow):
    with pytest.raises(CellError, match="Automatic mode"):
        build_controller(
            Settings(
                mode="automatic",
                commissioned=commissioned,
                commissioning_reference=reference,
                database=":memory:",
            ),
            allow,
        )
