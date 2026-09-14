import time

import cv2
import numpy as np
import pytest

from workcell.config import VisionConfig
from workcell.models import CellError
from workcell.vision import classify


def scene():
    return np.zeros((480, 640, 3), np.uint8), np.full((480, 640), 0.35, np.float32)


@pytest.mark.parametrize("part", ["red_cube", "blue_cylinder"])
def test_supported_fixture_silhouettes(part):
    color, depth = scene()
    if part == "red_cube":
        cv2.rectangle(color, (260, 180), (350, 270), (0, 0, 255), -1)
    else:
        cv2.circle(color, (320, 240), 45, (255, 0, 0), -1)
    detection = classify(color, depth, VisionConfig(), time.monotonic())
    assert detection.part == part
    assert detection.source == "hardware"
    assert detection.depth_mm == pytest.approx(350, abs=0.01)


def test_empty_scene_returns_no_detection():
    assert classify(*scene(), VisionConfig(), time.monotonic()) is None


def test_two_parts_are_rejected_instead_of_picking_largest():
    color, depth = scene()
    cv2.rectangle(color, (190, 180), (260, 250), (0, 0, 255), -1)
    cv2.circle(color, (390, 240), 35, (255, 0, 0), -1)
    with pytest.raises(CellError, match="Multiple parts"):
        classify(color, depth, VisionConfig(), time.monotonic())


def test_blue_box_is_not_misrouted_to_magazine():
    color, depth = scene()
    cv2.rectangle(color, (260, 180), (350, 270), (255, 0, 0), -1)
    with pytest.raises(CellError, match="Unsupported"):
        classify(color, depth, VisionConfig(), time.monotonic())


def test_depth_holes_do_not_count_as_valid_measurements():
    color, depth = scene()
    cv2.rectangle(color, (260, 180), (350, 270), (0, 0, 255), -1)
    depth[180:271, 260:351] = 0
    with pytest.raises(CellError, match="Insufficient valid depth"):
        classify(color, depth, VisionConfig(), time.monotonic())


def test_partial_part_at_roi_edge_is_rejected():
    color, depth = scene()
    cv2.rectangle(color, (100, 180), (250, 270), (0, 0, 255), -1)
    with pytest.raises(CellError, match="boundary"):
        classify(color, depth, VisionConfig(), time.monotonic())
