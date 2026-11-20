"""Zone-Based Spatial Occupancy, Entry/Exit, Intrusion, Vacancy & Crowd Analyzer.

Operates strictly on normalized anonymous person coordinates & ephemeral track IDs.
Never attributes detections to named individuals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.ai_vision.detector import PersonDetection


def point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """Ray-casting point-in-polygon check on normalized [0..1] coordinates."""
    if len(polygon) < 3:
        return False
    px, py = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        intersects = ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / ((yj - yi) + 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


@dataclass
class ZoneConfig:
    zone_id: int
    name: str
    zone_type: str  # workspace | entry_exit | restricted | common_area
    coordinates: List[List[float]]
    max_occupancy: int = 10
    vacancy_alert_minutes: int = 45
    last_occupied_at: Optional[datetime] = None


@dataclass
class DetectedEventCandidate:
    event_type: str
    severity: str
    zone_id: Optional[int]
    zone_name: Optional[str]
    person_count: int
    anonymous_track_ids: List[str]
    confidence: float
    description: str


@dataclass
class FrameAnalysisResult:
    total_persons: int
    zone_counts: Dict[int, int] = field(default_factory=dict)
    events: List[DetectedEventCandidate] = field(default_factory=list)


class ZoneAnalyzer:
    """Evaluates anonymous person detections against configured camera monitoring zones."""

    def analyze_frame(
        self,
        detections: List[PersonDetection],
        motion_vectors: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]],
        zones: List[ZoneConfig],
        camera_max_occupancy: int = 12,
        previous_zone_counts: Optional[Dict[int, int]] = None,
        now: Optional[datetime] = None,
    ) -> FrameAnalysisResult:
        current_time = now or datetime.now(timezone.utc)
        prev_counts = previous_zone_counts or {}
        result = FrameAnalysisResult(total_persons=len(detections))

        avg_conf = (
            round(sum(d.confidence for d in detections) / len(detections), 3)
            if detections
            else 0.95
        )

        for zone in zones:
            in_zone_tracks: List[str] = []
            for det in detections:
                if point_in_polygon(det.center_norm, zone.coordinates):
                    in_zone_tracks.append(det.track_id or "trk_anon")

            count = len(in_zone_tracks)
            result.zone_counts[zone.zone_id] = count
            prev_count = prev_counts.get(zone.zone_id, count)

            # 1. Restricted-area intrusion alert
            if zone.zone_type == "restricted" and count > 0:
                result.events.append(
                    DetectedEventCandidate(
                        event_type="restricted_intrusion",
                        severity="critical",
                        zone_id=zone.zone_id,
                        zone_name=zone.name,
                        person_count=count,
                        anonymous_track_ids=in_zone_tracks,
                        confidence=avg_conf,
                        description=(
                            f"Restricted zone '{zone.name}' detected {count} anonymous person(s). "
                            f"Authorized human review required."
                        ),
                    )
                )

            # 2. Entry / Exit crossing detection using short-lived motion vectors
            if zone.zone_type == "entry_exit":
                ys = [pt[1] for pt in zone.coordinates]
                mid_y = (min(ys) + max(ys)) / 2.0 if ys else 0.5
                entered_tracks: List[str] = []
                exited_tracks: List[str] = []
                for tid, (prev_c, curr_c) in motion_vectors.items():
                    if point_in_polygon(curr_c, zone.coordinates) or point_in_polygon(
                        prev_c, zone.coordinates
                    ):
                        if prev_c[1] < mid_y <= curr_c[1]:
                            entered_tracks.append(tid)
                        elif prev_c[1] > mid_y >= curr_c[1]:
                            exited_tracks.append(tid)
                if entered_tracks:
                    result.events.append(
                        DetectedEventCandidate(
                            event_type="entry",
                            severity="info",
                            zone_id=zone.zone_id,
                            zone_name=zone.name,
                            person_count=len(entered_tracks),
                            anonymous_track_ids=entered_tracks,
                            confidence=avg_conf,
                            description=(
                                f"Entry transition detected in '{zone.name}' "
                                f"({len(entered_tracks)} anonymous passage(s))."
                            ),
                        )
                    )
                if exited_tracks:
                    result.events.append(
                        DetectedEventCandidate(
                            event_type="exit",
                            severity="info",
                            zone_id=zone.zone_id,
                            zone_name=zone.name,
                            person_count=len(exited_tracks),
                            anonymous_track_ids=exited_tracks,
                            confidence=avg_conf,
                            description=(
                                f"Exit transition detected in '{zone.name}' "
                                f"({len(exited_tracks)} anonymous passage(s))."
                            ),
                        )
                    )

            # 3. Crowd / over-capacity detection
            if zone.max_occupancy > 0 and count > zone.max_occupancy:
                result.events.append(
                    DetectedEventCandidate(
                        event_type="crowd_detected",
                        severity="warning",
                        zone_id=zone.zone_id,
                        zone_name=zone.name,
                        person_count=count,
                        anonymous_track_ids=in_zone_tracks,
                        confidence=avg_conf,
                        description=(
                            f"Crowd threshold exceeded in '{zone.name}': "
                            f"{count} persons observed (limit: {zone.max_occupancy})."
                        ),
                    )
                )

            # 4. Extended workspace vacancy alert
            if zone.zone_type == "workspace" and count == 0 and zone.last_occupied_at is not None:
                last_occ = zone.last_occupied_at
                if last_occ.tzinfo is None:
                    last_occ = last_occ.replace(tzinfo=timezone.utc)
                vacant_for = current_time - last_occ
                if vacant_for >= timedelta(minutes=zone.vacancy_alert_minutes):
                    mins = int(vacant_for.total_seconds() // 60)
                    result.events.append(
                        DetectedEventCandidate(
                            event_type="extended_vacancy",
                            severity="info",
                            zone_id=zone.zone_id,
                            zone_name=zone.name,
                            person_count=0,
                            anonymous_track_ids=[],
                            confidence=0.98,
                            description=(
                                f"Workspace zone '{zone.name}' unoccupied for {mins} minutes "
                                f"(spatial utilization metric only; does not assess individual work)."
                            ),
                        )
                    )

            # 5. Significant occupancy change
            if abs(count - prev_count) >= 2:
                result.events.append(
                    DetectedEventCandidate(
                        event_type="occupancy_change",
                        severity="info",
                        zone_id=zone.zone_id,
                        zone_name=zone.name,
                        person_count=count,
                        anonymous_track_ids=in_zone_tracks,
                        confidence=avg_conf,
                        description=(
                            f"Zone '{zone.name}' occupancy shifted from {prev_count} to {count}."
                        ),
                    )
                )

        # Whole-camera crowd check if no zone caught it
        if camera_max_occupancy > 0 and len(detections) > camera_max_occupancy:
            already_crowded = any(e.event_type == "crowd_detected" for e in result.events)
            if not already_crowded:
                result.events.append(
                    DetectedEventCandidate(
                        event_type="crowd_detected",
                        severity="warning",
                        zone_id=None,
                        zone_name=None,
                        person_count=len(detections),
                        anonymous_track_ids=[d.track_id or "trk_anon" for d in detections],
                        confidence=avg_conf,
                        description=(
                            f"Camera area occupancy ({len(detections)}) exceeded "
                            f"configured capacity ({camera_max_occupancy})."
                        ),
                    )
                )

        return result


zone_analyzer = ZoneAnalyzer()
