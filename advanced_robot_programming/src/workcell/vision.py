import threading
import time

import cv2
import numpy as np

from workcell.config import VisionConfig
from workcell.models import CellError, Detection


def classify(color, depth, config: VisionConfig, captured_at: float):
    """Conservative fixture inspection: exactly one supported colored silhouette.

    Confidence is a geometric quality score, not a calibrated probability.
    This does not estimate a robot pickup pose or infer unseen 3D geometry.
    """
    x, y, w, h = config.roi
    crop = color[y : y + h, x : x + w]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    candidates = []
    for name, ranges in {
        "red": [((0, 100, 60), (12, 255, 255)), ((168, 100, 60), (180, 255, 255))],
        "blue": [((90, 100, 60), (135, 255, 255))],
    }.items():
        mask = np.zeros((h, w), dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < config.min_area_px:
                continue
            bx, by, bw, bh = cv2.boundingRect(contour)
            if bx <= 0 or by <= 0 or bx + bw >= w or by + bh >= h:
                raise CellError(
                    "Part touches inspection boundary; reposition it fully inside the fixture ROI"
                )
            perimeter = cv2.arcLength(contour, True)
            vertices = len(cv2.approxPolyDP(contour, perimeter * 0.025, True))
            rectangle = cv2.minAreaRect(contour)[1]
            fill = area / max(1, rectangle[0] * rectangle[1])
            circularity = 4 * np.pi * area / max(1, perimeter**2)
            part = None
            score = 0
            if name == "red" and vertices == 4 and fill >= 0.90:
                part, score = "red_cube", min(1, fill)
            elif name == "blue" and vertices >= 6 and circularity >= 0.82:
                part, score = "blue_cylinder", min(1, circularity)
            object_mask = np.zeros((h, w), np.uint8)
            cv2.drawContours(object_mask, [contour], -1, 255, -1)
            samples = depth[y : y + h, x : x + w][object_mask > 0]
            valid = samples[np.isfinite(samples) & (samples > 0.05) & (samples < 2)]
            if len(valid) / max(1, len(samples)) < config.min_depth_coverage:
                raise CellError("Insufficient valid depth on the detected part")
            if part is None:
                raise CellError("Unsupported color/shape combination")
            candidates.append(
                Detection(
                    part, float(score), captured_at, "hardware", float(np.median(valid) * 1000)
                )
            )
    if len(candidates) > 1:
        raise CellError("Multiple parts in the inspection region")
    return candidates[0] if candidates else None


class RealSenseCamera:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.pipeline = None
        self.thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.frame = None
        self.error = "Waiting for first camera frame"

    def start(self):
        import pyrealsense2 as rs

        self.pipeline = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(
            rs.stream.color, self.config.width, self.config.height, rs.format.bgr8, self.config.fps
        )
        cfg.enable_stream(
            rs.stream.depth, self.config.width, self.config.height, rs.format.z16, self.config.fps
        )
        profile = self.pipeline.start(cfg)
        self.scale = profile.get_device().first_depth_sensor().get_depth_scale()
        self.align = rs.align(rs.stream.color)
        self.thread = threading.Thread(target=self._capture, name="realsense", daemon=True)
        self.thread.start()

    def _capture(self):
        while not self.stop_event.is_set():
            try:
                frames = self.align.process(self.pipeline.wait_for_frames(timeout_ms=1000))
                color, depth = frames.get_color_frame(), frames.get_depth_frame()
                if not color or not depth:
                    raise CellError("Incomplete RGB-D frame")
                captured_at = time.monotonic()
                frame = (
                    np.asanyarray(color.get_data()).copy(),
                    np.asanyarray(depth.get_data()).astype(np.float32) * self.scale,
                    captured_at,
                )
                with self.lock:
                    self.frame, self.error = frame, None
            except Exception as exc:
                with self.lock:
                    self.frame, self.error = None, f"Camera capture failed: {exc}"
                self.stop_event.wait(0.1)

    def _latest(self):
        with self.lock:
            if self.error or self.frame is None:
                raise CellError(self.error or "No camera frame")
            if time.monotonic() - self.frame[2] > self.config.max_age_s:
                raise CellError("Camera frame is stale")
            return self.frame

    def inspect(self):
        color, depth, captured_at = self._latest()
        return classify(color, depth, self.config, captured_at)

    def jpeg(self):
        color, _, _ = self._latest()
        color = color.copy()
        x, y, w, h = self.config.roi
        cv2.rectangle(color, (x, y), (x + w, y + h), (100, 220, 180), 2)
        ok, data = cv2.imencode(".jpg", color, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return data.tobytes() if ok else None

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        if self.pipeline:
            try:
                self.pipeline.stop()
            except RuntimeError:
                pass  # start() may have failed before streaming began
            self.pipeline = None
