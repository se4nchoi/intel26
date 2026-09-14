import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workcell.models import CellError, Pose


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Workspace(StrictModel):
    x: tuple[float, float] = (-50, 650)
    y: tuple[float, float] = (100, 650)
    z: tuple[float, float] = (150, 650)

    @model_validator(mode="after")
    def ordered(self):
        if any(lo >= hi for lo, hi in (self.x, self.y, self.z)):
            raise ValueError("Workspace bounds must be increasing")
        return self

    def check(self, pose: Pose):
        for name, value, (lo, hi) in zip("XYZ", pose.values, (self.x, self.y, self.z)):
            if not lo <= value <= hi:
                raise CellError(f"{name}={value} mm is outside [{lo}, {hi}]")


class RobotConfig(StrictModel):
    host: str = "192.168.3.7"
    index: int = Field(0, ge=0, le=1)
    velocity_percent: float = Field(5, gt=0, le=10)
    acceleration_percent: float = Field(10, gt=0, le=20)
    rpc_timeout_s: float = Field(1, gt=0, le=5)
    motion_timeout_s: float = Field(30, gt=0, le=120)
    gripper_timeout_s: float = Field(3, gt=0, le=10)
    position_tolerance_mm: float = Field(1, gt=0, le=5)
    angle_tolerance_deg: float = Field(1, gt=0, le=5)
    close_do: int = Field(0, ge=0)
    close_do_active_high: bool = True
    closed_di: int = Field(0, ge=0)
    open_di: int = Field(1, ge=0)
    part_present_di: int = Field(2, ge=0)
    feedback_active_high: bool = True

    @model_validator(mode="after")
    def distinct_feedback(self):
        if len({self.closed_di, self.open_di, self.part_present_di}) != 3:
            raise ValueError("Open, closed, and part-present feedback must use distinct inputs")
        return self


class PLCConfig(StrictModel):
    host: str = "192.168.3.150"
    port: int = Field(5010, gt=0, le=65535)
    timeout_s: float = Field(1, gt=0, le=5)
    heartbeat_timeout_s: float = Field(3, gt=0, le=10)


class VisionConfig(StrictModel):
    width: int = Field(640, ge=320)
    height: int = Field(480, ge=240)
    fps: int = Field(30, gt=0, le=60)
    roi: tuple[int, int, int, int] = (160, 120, 320, 240)
    min_area_px: int = Field(1000, gt=0)
    min_confidence: float = Field(0.75, gt=0, le=1)
    max_age_s: float = Field(1, gt=0, le=5)
    min_depth_coverage: float = Field(0.8, gt=0, le=1)

    @model_validator(mode="after")
    def roi_in_frame(self):
        x, y, w, h = self.roi
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > self.width or y + h > self.height:
            raise ValueError("Vision ROI must fit within the camera frame")
        return self


class Recipe(StrictModel):
    pick: tuple[float, float, float, float, float, float] = (
        232.49,
        514.57,
        254.19,
        -19.52,
        -179.64,
        90.03,
    )
    pallet_base: tuple[float, float, float, float, float, float] = (
        201.75,
        219.29,
        304.94,
        -3.24,
        -179.44,
        90.01,
    )
    magazine: tuple[float, float, float, float, float, float] = (
        -8.15,
        515.98,
        343.32,
        -19.46,
        -177.65,
        90.01,
    )
    transfer_z_mm: float = 450
    columns: int = Field(2, ge=1, le=10)
    rows: int = Field(2, ge=1, le=10)
    layers: int = Field(2, ge=1, le=10)
    row_step_mm: float = Field(80, gt=0)
    column_step_mm: float = Field(80, gt=0)
    layer_step_mm: float = Field(30, gt=0)

    @property
    def capacity(self):
        return self.columns * self.rows * self.layers

    def slot_pose(self, index: int) -> Pose:
        if not 0 <= index < self.capacity:
            raise CellError("Pallet slot is out of range")
        layer, within = divmod(index, self.columns * self.rows)
        row, column = divmod(within, self.columns)
        x, y, z, *angles = self.pallet_base
        return Pose(
            (
                x - row * self.row_step_mm,
                y + column * self.column_step_mm,
                z + layer * self.layer_step_mm,
                *angles,
            )
        )


class Settings(StrictModel):
    mode: Literal["simulation", "observe", "automatic"] = "simulation"
    commissioned: bool = False
    commissioning_reference: str = ""
    database: str = "data/simulation.sqlite3"
    workspace: Workspace = Field(default_factory=Workspace)
    robot: RobotConfig = Field(default_factory=RobotConfig)
    plc: PLCConfig = Field(default_factory=PLCConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    recipe: Recipe = Field(default_factory=Recipe)

    @model_validator(mode="after")
    def valid_targets(self):
        targets = [Pose(self.recipe.pick), Pose(self.recipe.magazine)]
        targets += [self.recipe.slot_pose(i) for i in range(self.recipe.capacity)]
        for pose in targets:
            self.workspace.check(pose)
            self.workspace.check(pose.at_z(self.recipe.transfer_z_mm))
            if pose.values[2] >= self.recipe.transfer_z_mm:
                raise ValueError("Transfer plane must be above every pick/place target")
        return self

    @property
    def fingerprint(self) -> str:
        data = self.model_dump(exclude={"database"})
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def load_settings(path: Path | None = None) -> Settings:
    if path is None:
        return Settings()
    with path.open("rb") as stream:
        result = Settings.model_validate(tomllib.load(stream))
    database = Path(result.database)
    if not database.is_absolute():
        result.database = str((path.resolve().parent / database).resolve())
    return result
