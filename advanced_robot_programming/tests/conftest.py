import time

import pytest

from workcell.config import Settings
from workcell.controller import Controller
from workcell.models import Pose
from workcell.simulation import Scenario, SimCamera, SimPLC, SimRobot
from workcell.storage import Store


def settle(cell, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cell.initialized and not cell.pending:
            return cell.snapshot()
        time.sleep(0.005)
    raise AssertionError(f"Controller did not settle: {cell.snapshot()}")


def command(cell, action, **payload):
    cell.submit(action, **payload)
    return settle(cell)


@pytest.fixture
def cell():
    settings = Settings(database=":memory:")
    world = Scenario(delay=0)
    robot = SimRobot(world, Pose(settings.recipe.pick).at_z(settings.recipe.transfer_z_mm))
    controller = Controller(
        settings,
        Store(":memory:", 8, settings.fingerprint),
        robot,
        SimPLC(world),
        SimCamera(world),
        world,
    )
    controller.start()
    settle(controller)
    yield controller
    controller.close()
