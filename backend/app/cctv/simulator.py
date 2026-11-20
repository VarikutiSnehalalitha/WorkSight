"""Simulated CCTV Frame Generator for Local Development.

IMPORTANT: Every frame produced by this module carries an unmistakable
'SIMULATED DEV FEED — NOT LIVE CCTV' banner so simulated footage is never
mistaken for real physical camera video.
"""

import io
import json
import math
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


class SimulatedCameraFeed:
    """Renders deterministic, smooth synthetic office monitoring frames as JPEG bytes."""

    def __init__(self, width: int = 800, height: int = 450):
        self.width = width
        self.height = height

    def _get_font(self, size: int = 14) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

    def generate_frame_jpeg(
        self,
        camera_id: int,
        camera_name: str,
        location: str,
        occupancy: int,
        zones: Optional[List[Dict]] = None,
        status: str = "online",
        timestamp: Optional[float] = None,
    ) -> Tuple[bytes, List[Dict]]:
        """Generate a JPEG frame plus anonymous person detections for AI pipeline testing."""
        t = timestamp if timestamp is not None else time.time()
        img = Image.new("RGB", (self.width, self.height), color=(26, 31, 28))
        draw = ImageDraw.Draw(img)

        font_sm = self._get_font(12)
        font_md = self._get_font(15)
        font_lg = self._get_font(18)

        # If camera is offline or obstructed, render authentic status slate
        if status == "offline":
            draw.rectangle([(0, 0), (self.width, self.height)], fill=(20, 22, 21))
            draw.text(
                (self.width // 2 - 140, self.height // 2 - 20),
                "SIGNAL LOST — RECONNECTING...",
                fill=(220, 120, 90),
                font=font_lg,
            )
            self._draw_simulation_banner(draw, camera_name, location, font_sm, font_md)
            return self._encode_jpeg(img), []

        if status == "obstructed":
            draw.rectangle([(0, 0), (self.width, self.height)], fill=(14, 15, 14))
            draw.text(
                (self.width // 2 - 165, self.height // 2 - 20),
                "ALERT: CAMERA LENS OBSTRUCTED",
                fill=(235, 160, 80),
                font=font_lg,
            )
            self._draw_simulation_banner(draw, camera_name, location, font_sm, font_md)
            return self._encode_jpeg(img), []

        # Draw subtle architectural office floor grid
        for x in range(0, self.width, 40):
            draw.line([(x, 42), (x, self.height - 34)], fill=(36, 44, 40), width=1)
        for y in range(42, self.height - 34, 40):
            draw.line([(0, y), (self.width, y)], fill=(36, 44, 40), width=1)

        # Draw stylized office desks / architectural layout
        desk_color = (44, 54, 49)
        desk_outline = (68, 84, 76)
        for row in range(2):
            for col in range(3):
                dx = 85 + col * 230
                dy = 110 + row * 155
                draw.rectangle(
                    [(dx, dy), (dx + 145, dy + 68)],
                    fill=desk_color,
                    outline=desk_outline,
                    width=2,
                )
                draw.text((dx + 10, dy + 8), f"DESK {row * 3 + col + 1:02d}", fill=(120, 140, 130), font=font_sm)

        # Draw configured monitoring zones
        if zones:
            for z in zones:
                coords = z.get("coordinates", [])
                if isinstance(coords, str):
                    try:
                        coords = json.loads(coords)
                    except Exception:
                        coords = []
                if len(coords) >= 3:
                    pts = [(int(p[0] * self.width), int(p[1] * self.height)) for p in coords]
                    ztype = z.get("zone_type", "workspace")
                    color = (94, 168, 132) if ztype == "workspace" else (214, 152, 78)
                    if ztype == "restricted":
                        color = (214, 92, 82)
                    elif ztype == "entry_exit":
                        color = (118, 165, 210)
                    draw.polygon(pts, outline=color)
                    draw.text(
                        (pts[0][0] + 6, pts[0][1] + 6),
                        f"{z.get('name', 'Zone')} ({ztype.upper()})",
                        fill=color,
                        font=font_sm,
                    )

        # Render anonymous moving person silhouettes (NO faces / NO biometric features)
        detections: List[Dict] = []
        person_count = max(0, min(occupancy, 18))
        for idx in range(person_count):
            phase = (camera_id * 1.37) + (idx * 2.11)
            cx = int(120 + ((idx * 137 + math.sin(t * 0.45 + phase) * 65) % (self.width - 240)))
            cy = int(125 + ((idx * 89 + math.cos(t * 0.35 + phase) * 55) % (self.height - 210)))
            bw, bh = 38, 66
            x1, y1, x2, y2 = cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2

            # Anonymous silhouette body & head (blurred/abstract — privacy preserving)
            draw.ellipse([(cx - 10, y1 + 4), (cx + 10, y1 + 24)], fill=(185, 198, 190))
            draw.rounded_rectangle([(cx - 14, y1 + 25), (cx + 14, y2 - 4)], radius=6, fill=(140, 162, 150))

            # YOLO-style anonymous detection box
            draw.rectangle([(x1, y1), (x2, y2)], outline=(112, 196, 154), width=2)
            track_id = f"trk_{camera_id:02d}{idx + 1:02d}"
            conf = round(0.84 + 0.12 * abs(math.sin(t * 0.2 + idx)), 2)
            label = f"person {track_id} {conf:.2f}"
            draw.rectangle([(x1, y1 - 16), (x1 + 128, y1)], fill=(40, 75, 60))
            draw.text((x1 + 4, y1 - 14), label, fill=(242, 245, 240), font=font_sm)

            detections.append(
                {
                    "track_id": track_id,
                    "class": "person",
                    "confidence": conf,
                    "bbox_norm": [
                        round(x1 / self.width, 4),
                        round(y1 / self.height, 4),
                        round(x2 / self.width, 4),
                        round(y2 / self.height, 4),
                    ],
                    "center_norm": [round(cx / self.width, 4), round(cy / self.height, 4)],
                }
            )

        # Explicit top simulation disclosure banner & bottom telemetry HUD
        self._draw_simulation_banner(draw, camera_name, location, font_sm, font_md)

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        draw.rectangle([(0, self.height - 32), (self.width, self.height)], fill=(18, 22, 20))
        hud = (
            f"ANONYMOUS PERSON COUNT: {person_count}  |  "
            f"NO FACIAL RECOGNITION  |  "
            f"{now_str}"
        )
        draw.text((14, self.height - 24), hud, fill=(214, 222, 217), font=font_sm)

        return self._encode_jpeg(img), detections

    def _draw_simulation_banner(
        self,
        draw: ImageDraw.ImageDraw,
        camera_name: str,
        location: str,
        font_sm: ImageFont.ImageFont,
        font_md: ImageFont.ImageFont,
    ) -> None:
        draw.rectangle([(0, 0), (self.width, 38)], fill=(40, 75, 60))
        draw.rectangle([(10, 7), (262, 31)], fill=(180, 105, 62))
        draw.text((18, 12), "SIMULATED DEV FEED — NOT LIVE CCTV", fill=(255, 250, 245), font=font_sm)
        draw.text((276, 11), f"{camera_name}  •  {location}", fill=(247, 245, 240), font=font_md)

    @staticmethod
    def _encode_jpeg(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return buf.getvalue()


simulator_feed = SimulatedCameraFeed()
