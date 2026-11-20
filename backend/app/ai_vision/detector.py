"""YOLOv8 + PyTorch Anonymous Person Detector & Short-Lived Ephemeral Object Tracker.

Strictly limited to COCO class 0 ('person'). No face, emotion, or re-ID models.
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger("worksight.ai_vision")

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    OPENCV_AVAILABLE = False

try:
    import torch  # type: ignore
    from ultralytics import YOLO  # type: ignore

    YOLO_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    YOLO = None  # type: ignore
    YOLO_AVAILABLE = False


@dataclass
class PersonDetection:
    bbox_norm: Tuple[float, float, float, float]  # x1, y1, x2, y2 in [0, 1]
    center_norm: Tuple[float, float]
    confidence: float
    track_id: Optional[str] = None


@dataclass
class _TrackState:
    track_id: str
    bbox_norm: Tuple[float, float, float, float]
    center_norm: Tuple[float, float]
    prev_center_norm: Tuple[float, float]
    last_seen_ts: float
    frames_seen: int = 1


class EphemeralObjectTracker:
    """Short-lived centroid + IoU tracker for anonymous event correlation.

    Tracks automatically expire after `max_age_seconds` so no persistent identity
    is ever stored or inferred across sessions.
    """

    def __init__(self, max_distance: float = 0.14, max_age_seconds: float = 10.0) -> None:
        self.max_distance = max_distance
        self.max_age_seconds = max_age_seconds
        self._tracks: Dict[str, _TrackState] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter = (self._counter % 9999) + 1
        return f"trk_{self._counter:04d}"

    @staticmethod
    def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def update(
        self, detections: List[PersonDetection], now: Optional[float] = None
    ) -> Tuple[List[PersonDetection], Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]]:
        """Assign ephemeral track IDs and return per-track (prev_center, curr_center) motion vectors."""
        ts = now if now is not None else time.time()

        # Expire stale tracks
        expired = [
            tid
            for tid, st in self._tracks.items()
            if (ts - st.last_seen_ts) > self.max_age_seconds
        ]
        for tid in expired:
            del self._tracks[tid]

        matched_track_ids = set()
        motion_vectors: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {}

        for det in detections:
            best_tid: Optional[str] = None
            best_dist = self.max_distance
            for tid, state in self._tracks.items():
                if tid in matched_track_ids:
                    continue
                dist = self._distance(det.center_norm, state.center_norm)
                if dist < best_dist:
                    best_dist = dist
                    best_tid = tid

            if best_tid is not None:
                state = self._tracks[best_tid]
                prev_center = state.center_norm
                state.prev_center_norm = prev_center
                state.center_norm = det.center_norm
                state.bbox_norm = det.bbox_norm
                state.last_seen_ts = ts
                state.frames_seen += 1
                det.track_id = best_tid
                matched_track_ids.add(best_tid)
                motion_vectors[best_tid] = (prev_center, det.center_norm)
            else:
                new_tid = self._next_id()
                self._tracks[new_tid] = _TrackState(
                    track_id=new_tid,
                    bbox_norm=det.bbox_norm,
                    center_norm=det.center_norm,
                    prev_center_norm=det.center_norm,
                    last_seen_ts=ts,
                )
                det.track_id = new_tid
                matched_track_ids.add(new_tid)
                motion_vectors[new_tid] = (det.center_norm, det.center_norm)

        return detections, motion_vectors


class AnonymousPersonDetector:
    """Wraps YOLOv8 (PyTorch) for person-only detection with graceful OpenCV fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None
        self._backend = "unavailable"
        self._initialized = False

    def _ensure_loaded(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if YOLO_AVAILABLE and YOLO is not None:
            try:
                device = "cuda" if (self.settings.AI_USE_GPU and torch.cuda.is_available()) else "cpu"
                self._model = YOLO(self.settings.AI_MODEL_PATH)
                self._model.to(device)
                self._backend = f"yolov8-pytorch ({device})"
                logger.info("Loaded YOLOv8 person detector on %s", device)
                return
            except Exception as exc:
                logger.warning("Failed to initialize YOLOv8 model (%s); falling back.", exc)

        if OPENCV_AVAILABLE and cv2 is not None:
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self._model = hog
            self._backend = "opencv-hog-person"
            logger.info("Using OpenCV HOG person detector fallback.")
        else:
            self._backend = "lightweight-telemetry-mode"

    @property
    def backend_name(self) -> str:
        self._ensure_loaded()
        return self._backend

    def detect_persons_from_bgr(self, frame) -> List[PersonDetection]:
        """Run person-only detection (COCO class 0) on an OpenCV BGR frame."""
        self._ensure_loaded()
        if frame is None or not OPENCV_AVAILABLE:
            return []

        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return []

        results_out: List[PersonDetection] = []
        conf_thresh = self.settings.AI_PERSON_CONFIDENCE_THRESHOLD

        if self._backend.startswith("yolov8-pytorch") and self._model is not None:
            # classes=[0] enforces COCO 'person' detection ONLY
            preds = self._model.predict(
                source=frame,
                classes=[0],
                conf=conf_thresh,
                verbose=False,
            )
            for res in preds:
                if res.boxes is None:
                    continue
                for box in res.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0].item())
                    cx = ((x1 + x2) / 2.0) / w
                    cy = ((y1 + y2) / 2.0) / h
                    results_out.append(
                        PersonDetection(
                            bbox_norm=(x1 / w, y1 / h, x2 / w, y2 / h),
                            center_norm=(cx, cy),
                            confidence=round(conf, 3),
                        )
                    )
        elif self._backend == "opencv-hog-person" and self._model is not None:
            rects, weights = self._model.detectMultiScale(
                frame, winStride=(8, 8), padding=(8, 8), scale=1.05
            )
            for (x, y, bw, bh), weight in zip(rects, weights):
                conf = min(0.99, max(0.35, float(weight)))
                if conf < conf_thresh:
                    continue
                x1, y1, x2, y2 = x / w, y / h, (x + bw) / w, (y + bh) / h
                results_out.append(
                    PersonDetection(
                        bbox_norm=(x1, y1, x2, y2),
                        center_norm=((x1 + x2) / 2.0, (y1 + y2) / 2.0),
                        confidence=round(conf, 3),
                    )
                )

        return results_out


person_detector = AnonymousPersonDetector()
