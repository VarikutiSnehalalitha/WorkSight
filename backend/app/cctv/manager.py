"""RTSP / OpenCV Camera Stream Manager with Health Monitoring & Auto-Reconnection.

Credentials are decrypted strictly in-memory inside this worker module and
are NEVER logged or returned to API clients.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional

from app.cctv.simulator import simulator_feed
from app.core.security import decrypt_secret

logger = logging.getLogger("worksight.cctv")

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    OPENCV_AVAILABLE = False


@dataclass
class StreamHealth:
    camera_id: int
    status: str = "online"
    last_frame_ts: float = 0.0
    reconnect_attempts: int = 0
    fps: float = 0.0
    resolution: str = "1280x720"
    is_obstructed: bool = False


class CameraStreamManager:
    """Manages RTSP camera captures, backoff reconnections, and MJPEG frame delivery."""

    def __init__(self) -> None:
        self._health: Dict[int, StreamHealth] = {}
        self._max_backoff_seconds = 30

    def get_health(self, camera_id: int) -> StreamHealth:
        if camera_id not in self._health:
            self._health[camera_id] = StreamHealth(camera_id=camera_id, last_frame_ts=time.time())
        return self._health[camera_id]

    @staticmethod
    def build_authenticated_rtsp_url(
        rtsp_url_encrypted: Optional[str],
        username_encrypted: Optional[str],
        password_encrypted: Optional[str],
    ) -> Optional[str]:
        """Decrypt credentials in-memory to construct an RTSP URI for OpenCV VideoCapture."""
        raw_url = decrypt_secret(rtsp_url_encrypted)
        if not raw_url:
            return None
        username = decrypt_secret(username_encrypted)
        password = decrypt_secret(password_encrypted)
        if username and "@" not in raw_url and "://" in raw_url:
            scheme, rest = raw_url.split("://", 1)
            creds = f"{username}:{password or ''}"
            return f"{scheme}://{creds}@{rest}"
        return raw_url

    @staticmethod
    def is_frame_obstructed(frame) -> bool:
        """Detect blacked-out, covered, or uniform-color obstructed CCTV lenses."""
        if not OPENCV_AVAILABLE or frame is None:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_intensity = float(np.mean(gray))
        std_intensity = float(np.std(gray))
        # Covered lens produces very low luminance or near-zero variance
        return mean_intensity < 12.0 or std_intensity < 5.0

    def capture_single_rtsp_frame(
        self,
        camera_id: int,
        rtsp_url_encrypted: Optional[str],
        username_encrypted: Optional[str],
        password_encrypted: Optional[str],
    ) -> Optional[bytes]:
        """Attempt to grab a single frame from a physical RTSP camera using OpenCV."""
        if not OPENCV_AVAILABLE:
            return None
        auth_url = self.build_authenticated_rtsp_url(
            rtsp_url_encrypted, username_encrypted, password_encrypted
        )
        if not auth_url:
            return None

        health = self.get_health(camera_id)
        cap = cv2.VideoCapture(auth_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000)
        try:
            if not cap.isOpened():
                health.status = "reconnecting"
                health.reconnect_attempts += 1
                return None

            ok, frame = cap.read()
            if not ok or frame is None:
                health.status = "degraded"
                health.reconnect_attempts += 1
                return None

            h, w = frame.shape[:2]
            health.resolution = f"{w}x{h}"
            health.fps = float(cap.get(cv2.CAP_PROP_FPS) or 15.0)
            health.last_frame_ts = time.time()
            health.reconnect_attempts = 0
            health.is_obstructed = self.is_frame_obstructed(frame)
            health.status = "obstructed" if health.is_obstructed else "online"

            ok_enc, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            return jpeg.tobytes() if ok_enc else None
        finally:
            cap.release()

    async def mjpeg_stream_generator(
        self,
        camera_id: int,
        camera_name: str,
        location: str,
        is_simulated: bool,
        occupancy: int,
        zones: List[Dict],
        status: str,
        rtsp_url_encrypted: Optional[str] = None,
        username_encrypted: Optional[str] = None,
        password_encrypted: Optional[str] = None,
        fps: float = 4.0,
    ) -> AsyncGenerator[bytes, None]:
        """Yield multipart/x-mixed-replace MJPEG frames for authorized live viewing."""
        frame_delay = max(0.15, 1.0 / max(fps, 1.0))
        backoff = 1.0

        while True:
            frame_bytes: Optional[bytes] = None
            if is_simulated:
                frame_bytes, _ = simulator_feed.generate_frame_jpeg(
                    camera_id=camera_id,
                    camera_name=camera_name,
                    location=location,
                    occupancy=occupancy,
                    zones=zones,
                    status=status,
                )
            else:
                frame_bytes = await asyncio.to_thread(
                    self.capture_single_rtsp_frame,
                    camera_id,
                    rtsp_url_encrypted,
                    username_encrypted,
                    password_encrypted,
                )
                if frame_bytes is None:
                    # Emit clear offline/reconnecting placeholder without pretending it's live
                    frame_bytes, _ = simulator_feed.generate_frame_jpeg(
                        camera_id=camera_id,
                        camera_name=f"{camera_name} [RTSP Reconnecting]",
                        location=location,
                        occupancy=0,
                        zones=[],
                        status="offline",
                    )
                    await asyncio.sleep(min(backoff, self._max_backoff_seconds))
                    backoff = min(backoff * 1.5, self._max_backoff_seconds)
                else:
                    backoff = 1.0

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            await asyncio.sleep(frame_delay)


stream_manager = CameraStreamManager()
