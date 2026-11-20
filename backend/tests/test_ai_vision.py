"""Unit Tests for AI Computer Vision Tracker & Zone Spatial Analytics."""

from datetime import datetime, timedelta, timezone

from app.ai_vision.detector import EphemeralObjectTracker, PersonDetection
from app.ai_vision.zone_analyzer import ZoneAnalyzer, ZoneConfig, point_in_polygon


def test_point_in_polygon():
    square = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]
    assert point_in_polygon((0.5, 0.5), square) is True
    assert point_in_polygon((0.1, 0.1), square) is False


def test_ephemeral_tracker_assigns_anonymous_ids_and_expires():
    tracker = EphemeralObjectTracker(max_distance=0.2, max_age_seconds=5.0)
    d1 = [PersonDetection(bbox_norm=(0.2, 0.2, 0.3, 0.4), center_norm=(0.25, 0.3), confidence=0.9)]
    tracked_1, _ = tracker.update(d1, now=100.0)
    tid_1 = tracked_1[0].track_id
    assert tid_1.startswith("trk_")

    # Slight movement keeps same ephemeral track ID
    d2 = [PersonDetection(bbox_norm=(0.22, 0.22, 0.32, 0.42), center_norm=(0.27, 0.32), confidence=0.92)]
    tracked_2, motion = tracker.update(d2, now=101.0)
    assert tracked_2[0].track_id == tid_1
    assert tid_1 in motion

    # After expiration window, track is purged and new anonymous ID is issued
    d3 = [PersonDetection(bbox_norm=(0.22, 0.22, 0.32, 0.42), center_norm=(0.27, 0.32), confidence=0.91)]
    tracked_3, _ = tracker.update(d3, now=120.0)
    assert tracked_3[0].track_id != tid_1


def test_zone_analyzer_detects_intrusion_crowd_vacancy_and_entry():
    analyzer = ZoneAnalyzer()
    now = datetime.now(timezone.utc)

    zones = [
        ZoneConfig(
            zone_id=1,
            name="Restricted Server Vault",
            zone_type="restricted",
            coordinates=[[0.0, 0.0], [0.4, 0.0], [0.4, 0.4], [0.0, 0.4]],
            max_occupancy=0,
        ),
        ZoneConfig(
            zone_id=2,
            name="Main Lobby Entry",
            zone_type="entry_exit",
            coordinates=[[0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]],
            max_occupancy=5,
        ),
        ZoneConfig(
            zone_id=3,
            name="Design Workspace",
            zone_type="workspace",
            coordinates=[[0.5, 0.6], [1.0, 0.6], [1.0, 1.0], [0.5, 1.0]],
            max_occupancy=2,
            vacancy_alert_minutes=30,
            last_occupied_at=now - timedelta(minutes=60),
        ),
    ]

    detections = [
        PersonDetection((0.1, 0.1, 0.2, 0.2), (0.15, 0.15), 0.93, track_id="trk_0001"),
        PersonDetection((0.7, 0.3, 0.8, 0.4), (0.75, 0.35), 0.91, track_id="trk_0002"),
    ]
    # trk_0002 crossed downward across entry_exit zone midpoint (y=0.25)
    motion = {
        "trk_0001": ((0.14, 0.14), (0.15, 0.15)),
        "trk_0002": ((0.75, 0.15), (0.75, 0.35)),
    }

    res = analyzer.analyze_frame(detections=detections, motion_vectors=motion, zones=zones, now=now)
    event_types = {e.event_type for e in res.events}

    assert "restricted_intrusion" in event_types
    assert "entry" in event_types
    assert "extended_vacancy" in event_types
    assert res.zone_counts[1] == 1
    assert res.zone_counts[3] == 0
