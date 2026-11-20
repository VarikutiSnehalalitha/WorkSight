"""AI Computer Vision Monitoring Events & Human-in-the-Loop Review Endpoints."""

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_AND_HR,
    MANAGEMENT_ROLES,
    ROLE_DEPT_MANAGER,
    require_roles,
)
from app.core.database import get_db
from app.models.models import Camera, Notification, RetentionPolicy, User, VisionEvent
from app.schemas.schemas import (
    SimulateVisionEventRequest,
    VisionEventResponse,
    VisionEventReviewRequest,
)
from app.services.audit import log_audit
from app.services.realtime import realtime_hub

router = APIRouter(prefix="/api/events", tags=["AI Vision Events"])


def serialize_vision_event(ev: VisionEvent) -> VisionEventResponse:
    try:
        tids = json.loads(ev.anonymous_track_ids_json)
    except Exception:
        tids = []
    return VisionEventResponse(
        id=ev.id,
        camera_id=ev.camera_id,
        camera_name=ev.camera.name if ev.camera else f"Camera #{ev.camera_id}",
        camera_location=ev.camera.location if ev.camera else "Unknown",
        zone_id=ev.zone_id,
        zone_name=ev.zone.name if ev.zone else None,
        event_type=ev.event_type,
        source_category=ev.source_category,
        severity=ev.severity,
        person_count=ev.person_count,
        anonymous_track_ids=tids,
        confidence=ev.confidence,
        description=ev.description,
        is_simulated=ev.is_simulated,
        review_status=ev.review_status,
        reviewed_by_name=ev.reviewer.full_name if ev.reviewer else None,
        review_notes=ev.review_notes,
        reviewed_at=ev.reviewed_at,
        occurred_at=ev.occurred_at,
    )


@router.get("", response_model=List[VisionEventResponse])
def list_vision_events(
    event_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    review_status: Optional[str] = Query(default=None),
    camera_id: Optional[int] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    q = db.query(VisionEvent).join(Camera)
    if current_user.role == ROLE_DEPT_MANAGER:
        q = q.filter(Camera.department_id == current_user.managed_department_id)
    if event_type:
        q = q.filter(VisionEvent.event_type == event_type)
    if severity:
        q = q.filter(VisionEvent.severity == severity)
    if review_status:
        q = q.filter(VisionEvent.review_status == review_status)
    if camera_id is not None:
        q = q.filter(VisionEvent.camera_id == camera_id)

    events = q.order_by(VisionEvent.occurred_at.desc()).limit(limit).all()
    return [serialize_vision_event(e) for e in events]


@router.post("/{event_id}/review", response_model=VisionEventResponse)
def review_vision_event(
    event_id: int,
    payload: VisionEventReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    """Human review & correction workflow for AI Vision alerts."""
    ev = db.query(VisionEvent).filter(VisionEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Monitoring event not found.")

    if (
        current_user.role == ROLE_DEPT_MANAGER
        and ev.camera
        and ev.camera.department_id != current_user.managed_department_id
    ):
        raise HTTPException(status_code=403, detail="Cannot review events outside your department.")

    ev.review_status = payload.review_status
    ev.review_notes = payload.review_notes
    ev.reviewed_by_user_id = current_user.id
    ev.reviewed_at = datetime.now(timezone.utc)

    # Also update linked notifications if resolved or marked false positive
    linked_notifs = db.query(Notification).filter(Notification.related_event_id == ev.id).all()
    for n in linked_notifs:
        n.is_read = True
        n.review_status = "dismissed" if payload.review_status == "false_positive" else "resolved"
        n.review_notes = payload.review_notes
        n.reviewed_by_user_id = current_user.id

    db.commit()
    db.refresh(ev)

    log_audit(
        db=db,
        action=f"vision_event_{payload.review_status}",
        resource_type="vision_event",
        resource_id=str(ev.id),
        details=f"Human reviewer marked event #{ev.id} ({ev.event_type}) as {payload.review_status}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return serialize_vision_event(ev)


@router.post("/simulate", response_model=VisionEventResponse, status_code=201)
async def trigger_simulated_event(
    payload: SimulateVisionEventRequest,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    """Developer/Demo helper to trigger a clearly marked SIMULATED AI vision event & real-time WebSocket alert."""
    cam = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    now = datetime.now(timezone.utc)
    policy = db.query(RetentionPolicy).first()
    retention_days = policy.event_metadata_retention_days if policy else 90

    severity_map = {
        "entry": "info",
        "exit": "info",
        "occupancy_change": "info",
        "extended_vacancy": "info",
        "crowd_detected": "warning",
        "camera_obstructed": "critical",
        "camera_disconnected": "warning",
        "restricted_intrusion": "critical",
    }
    sev = severity_map.get(payload.event_type, "info")

    desc_map = {
        "entry": f"[SIMULATED] Anonymous entry transition recorded at {cam.name} ({payload.person_count} person(s)).",
        "exit": f"[SIMULATED] Anonymous exit transition recorded at {cam.name} ({payload.person_count} person(s)).",
        "occupancy_change": f"[SIMULATED] Workspace occupancy updated to {payload.person_count} anonymous person(s) at {cam.name}.",
        "extended_vacancy": f"[SIMULATED] Workspace zone at {cam.name} observed vacant past configured threshold (spatial metric only).",
        "crowd_detected": f"[SIMULATED] Crowd threshold exceeded at {cam.name}: {payload.person_count} anonymous persons observed.",
        "camera_obstructed": f"[SIMULATED] Potential lens obstruction detected on {cam.name}. Immediate technical check advised.",
        "camera_disconnected": f"[SIMULATED] Stream heartbeat lost on {cam.name}; automatic reconnection sequence initiated.",
        "restricted_intrusion": f"[SIMULATED] Anonymous person entered restricted perimeter monitored by {cam.name}. Human review required.",
    }

    zone_id = cam.zones[0].id if cam.zones else None
    tids = [f"trk_sim_{i + 1:02d}" for i in range(min(payload.person_count, 8))]

    ev = VisionEvent(
        camera_id=cam.id,
        zone_id=zone_id,
        event_type=payload.event_type,
        source_category="ai_presence_telemetry",
        severity=sev,
        person_count=payload.person_count,
        anonymous_track_ids_json=json.dumps(tids),
        confidence=0.92,
        description=desc_map[payload.event_type],
        is_simulated=True,
        review_status="unreviewed",
        occurred_at=now,
        expires_at=now + timedelta(days=retention_days),
    )
    db.add(ev)

    # Reflect status/occupancy on camera
    if payload.event_type == "camera_disconnected":
        cam.status = "offline"
        cam.reconnect_attempts += 1
    elif payload.event_type == "camera_obstructed":
        cam.status = "obstructed"
    else:
        cam.status = "online"
        cam.current_occupancy = payload.person_count
        cam.last_heartbeat_at = now
        if cam.zones:
            cam.zones[0].current_count = payload.person_count

    db.flush()

    cat_map = {
        "restricted_intrusion": "restricted_area",
        "extended_vacancy": "vacancy",
        "camera_obstructed": "camera",
        "camera_disconnected": "camera",
    }
    notif = Notification(
        title=f"[SIMULATED] {cam.name}: {payload.event_type.replace('_', ' ').title()}",
        message=ev.description,
        category=cat_map.get(payload.event_type, "occupancy"),
        severity=sev,
        target_roles="super_admin,hr_admin,dept_manager",
        department_id=cam.department_id,
        related_event_id=ev.id,
    )
    db.add(notif)
    db.commit()
    db.refresh(ev)

    serialized = serialize_vision_event(ev)
    await realtime_hub.broadcast(
        event_type="vision_event",
        payload={
            "event_id": ev.id,
            "camera_id": cam.id,
            "camera_name": cam.name,
            "event_type": ev.event_type,
            "severity": ev.severity,
            "person_count": ev.person_count,
            "description": ev.description,
            "is_simulated": True,
        },
        allowed_roles={"super_admin", "hr_admin", "dept_manager"},
        department_id=cam.department_id,
    )

    return serialized
