from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Callable, Protocol


class CellError(Exception):
    """An actionable, latched cell fault or rejected command."""


class State(StrEnum):
    DISABLED = "DISABLED"
    READY = "READY"
    INSPECTING = "INSPECTING"
    PLANNING = "PLANNING"
    PICKING = "PICKING"
    VERIFYING_GRIP = "VERIFYING_GRIP"
    PLACING = "PLACING"
    VERIFYING_RELEASE = "VERIFYING_RELEASE"
    RETREATING = "RETREATING"
    COMPLETE = "COMPLETE"
    WAITING_FOR_PALLET_CHANGE = "WAITING_FOR_PALLET_CHANGE"
    FAULT = "FAULT"


@dataclass(frozen=True)
class Pose:
    values: tuple[float, ...]

    def __post_init__(self):
        if len(self.values) != 6 or not all(isfinite(v) for v in self.values):
            raise ValueError("A pose needs six finite values: X Y Z (mm), RX RY RZ (degrees)")

    def at_z(self, z: float) -> "Pose":
        return Pose((*self.values[:2], z, *self.values[3:]))


@dataclass(frozen=True)
class Detection:
    part: str
    confidence: float
    captured_at: float
    source: str
    depth_mm: float | None = None


@dataclass(frozen=True)
class Interlocks:
    permit: bool
    estop: bool
    request_id: int
    captured_at: float


Guard = Callable[[], None]


class Robot(Protocol):
    def connect(self) -> None: ...
    def status(self) -> dict: ...
    def move(self, pose: Pose, guard: Guard) -> None: ...
    def grip(self, closed: bool, guard: Guard) -> None: ...
    def verify_grip(self, closed: bool, guard: Guard) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class PLC(Protocol):
    def connect(self) -> None: ...
    def read(self) -> Interlocks: ...
    def publish(self, request_id: int, state: State, slot: int | None) -> None: ...
    def close(self) -> None: ...


class Camera(Protocol):
    def start(self) -> None: ...
    def inspect(self) -> Detection | None: ...
    def jpeg(self) -> bytes | None: ...
    def close(self) -> None: ...
