"""Camera RTSP Connection Testing Service."""

import socket
import time
from typing import Optional
from urllib.parse import urlparse

from app.cctv.manager import OPENCV_AVAILABLE, cv2
from app.core.security import mask_stream_endpoint


def test_camera_connection(
    rtsp_url: Optional[str],
    username: Optional[str] = None,
    password: Optional[str] = None,
    is_simulated: bool = False,
) -> dict:
    """Validate connectivity to a real RTSP camera or simulated dev generator.

    Returns masked endpoint info and never echoes credentials back.
    """
    start = time.perf_counter()
    masked = mask_stream_endpoint(rtsp_url, is_simulated=is_simulated)

    if is_simulated:
        latency_ms = round((time.perf_counter() - start) * 1000 + 8.5, 2)
        return {
            "reachable": True,
            "is_simulated": True,
            "masked_endpoint": masked,
            "resolution": "1280x720",
            "fps": 15.0,
            "latency_ms": latency_ms,
            "message": "Simulated development camera generator verified (clearly marked as non-live).",
        }

    if not rtsp_url or not rtsp_url.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        return {
            "reachable": False,
            "is_simulated": False,
            "masked_endpoint": masked,
            "resolution": None,
            "fps": None,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "message": "Invalid stream URL. Expected rtsp:// or rtsps:// endpoint.",
        }

    parsed = urlparse(rtsp_url)
    host = parsed.hostname
    port = parsed.port or (554 if parsed.scheme.startswith("rtsp") else 80)

    if not host:
        return {
            "reachable": False,
            "is_simulated": False,
            "masked_endpoint": masked,
            "resolution": None,
            "fps": None,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "message": "Could not parse camera host from URL.",
        }

    # Step 1: Fast TCP reachability check
    try:
        with socket.create_connection((host, port), timeout=3.0):
            pass
    except OSError as exc:
        return {
            "reachable": False,
            "is_simulated": False,
            "masked_endpoint": masked,
            "resolution": None,
            "fps": None,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "message": f"Unable to reach camera host {host}:{port} ({exc.__class__.__name__}).",
        }

    # Step 2: OpenCV RTSP handshake if OpenCV is installed
    if OPENCV_AVAILABLE and cv2 is not None:
        auth_url = rtsp_url
        if username and "@" not in rtsp_url and "://" in rtsp_url:
            scheme, rest = rtsp_url.split("://", 1)
            auth_url = f"{scheme}://{username}:{password or ''}@{rest}"
        cap = cv2.VideoCapture(auth_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000)
        try:
            if cap.isOpened():
                ok, frame = cap.read()
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                if ok and frame is not None:
                    h, w = frame.shape[:2]
                    fps = float(cap.get(cv2.CAP_PROP_FPS) or 15.0)
                    return {
                        "reachable": True,
                        "is_simulated": False,
                        "masked_endpoint": masked,
                        "resolution": f"{w}x{h}",
                        "fps": round(fps, 1),
                        "latency_ms": latency_ms,
                        "message": "RTSP video stream verified via OpenCV.",
                    }
        finally:
            cap.release()

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    return {
        "reachable": True,
        "is_simulated": False,
        "masked_endpoint": masked,
        "resolution": "Pending OpenCV decode",
        "fps": 15.0,
        "latency_ms": latency_ms,
        "message": "TCP port reachable. Install requirements-ai.txt for full OpenCV frame decoding.",
    }
