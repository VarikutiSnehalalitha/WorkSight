"""AI Vision Event Pipeline connecting Camera Frames -> YOLO -> Zone Analytics -> DB & Notifications."""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.ai_vision.detector import EphemeralObjectTracker, PersonDetection
from app.ai_vision.zone_analyzer import ZoneConfig, zone_analyzer
from app.models.models import Camera, Notification, RetentionPolicy, VisionEvent


class VisionPipeline:
    """Orchestrates anonymous person analytics per camera."""

    def __init__(self) -> None:
        self._trackers: Dict[int, EphemeralObjectTracker] = {}
        self._last_zone_counts: Dict[int, Dict[int, int]] = {}

    def _get_tracker(self, camera_id: int) -> EphemeralObjectTracker:
        if camera_id not in self._trackers:
            self._trackers[camera_id] = EphemeralObjectTracker()
        return self._trackers[camera_id]

    def process_detections_for_camera(
        self,
        db: Session,
        camera: Camera,
        detections: List[PersonDetection],
    ) -> List[VisionEvent]:
        """Run tracker + zone analyzer on a batch of anonymous detections and persist events."""
        tracker = self._get_tracker(camera.id)
        tracked, motion_vectors = tracker.update(detections)

        zone_configs: List[ZoneConfig] = []
        for z in camera.zones:
            if not z.is_active:
                continue
            try:
                coords = json.loads(z.coordinates_json)
            except Exception:
                coords = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
            zone_configs.append(
                ZoneConfig(
                    zone_id=z.id,
                    name=z.name,
                    zone_type=z.zone_type,
                    coordinates=coords,
                    max_occupancy=z.max_occupancy,
                    vacancy_alert_minutes=z.vacancy_alert_minutes,
                    last_occupied_at=z.last_occupied_at,
                )
            )

        prev_counts = self._last_zone_counts.get(camera.id, {})
        now = datetime.now(timezone.utc)
        analysis = zone_analyzer.analyze_frame(
            detections=tracked,
            motion_vectors=motion_vectors,
            zones=zone_configs,
            camera_max_occupancy=camera.max_occupancy_threshold,
            previous_zone_counts=prev_counts,
            now=now,
        )

        self._last_zone_counts[camera.id] = analysis.zone_counts
        camera.current_occupancy = analysis.total_persons
        camera.last_heartbeat_at = now

        for z in camera.zones:
            if z.id in analysis.zone_counts:
                z.current_count = analysis.zone_counts[z.id]
                if z.current_count > 0:
                    z.last_occupied_at = now

        policy = db.query(RetentionPolicy).first()
        retention_days = policy.event_metadata_retention_days if policy else 90
        expires_at = now + timedelta(days=retention_days)

        created_events: List[VisionEvent] = []
        for cand in analysis.events:
            ev = VisionEvent(
                camera_id=camera.id,
                zone_id=cand.zone_id,
                event_type=cand.event_type,
                source_category="ai_presence_telemetry",
                severity=cand.severity,
                person_count=cand.person_count,
                anonymous_track_ids_json=json.dumps(cand.anonymous_track_ids),
                confidence=cand.confidence,
                description=cand.description,
                is_simulated=camera.is_simulated,
                review_status="unreviewed",
                occurred_at=now,
                expires_at=expires_at,
            )
            db.add(ev)
            db.flush()
            created_events.append(ev)

            if cand.severity in ("warning", "critical") or cand.event_type in (
                "restricted_intrusion",
                "crowd_detected",
                "extended_vacancy",
                "camera_obstructed",
                "camera_disconnected",
            ):
                category = {
                    "restricted_intrusion": "restricted_area",
                    "extended_vacancy": "vacancy",
                    "camera_obstructed": "camera",
                    "camera_disconnected": "camera",
                }.get(cand.event_type, "occupancy")
                notif = Notification(
                    title=f"{camera.name}: {cand.event_type.replace('_', ' ').title()}",
                    message=cand.description,
                    category=category,
                    severity=cand.severity,
                    target_roles="super_admin,hr_admin,dept_manager",
                    department_id=camera.department_id,
                    related_event_id=ev.id,
                )
                db.add(notif)

        db.commit()
        return created_events


vision_pipeline = VisionPipeline()
