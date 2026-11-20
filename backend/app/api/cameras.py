"""CCTV Management, Encrypted Credentials, ONVIF Discovery, Zones & Authorized Live Streaming."""

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import ROLE_HR_ADMIN, ROLE_SUPER_ADMIN, require_cctv_access
from app.cctv.manager import stream_manager
from app.cctv.onvif_discovery import discover_onvif_cameras
from app.cctv.simulator import simulator_feed
from app.cctv.stream_tester import test_camera_connection
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_stream_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    mask_stream_endpoint,
)
from app.models.models import Camera, MonitoringZone, User
from app.schemas.schemas import (
    CameraConnectionTestRequest,
    CameraConnectionTestResponse,
    CameraCreate,
    CameraResponse,
    CameraUpdate,
    MonitoringZoneCreate,
    MonitoringZoneResponse,
    OnvifDeviceDiscovered,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/api/cameras", tags=["CCTV Monitoring"])


def serialize_zone(z: MonitoringZone) -> MonitoringZoneResponse:
    try:
        coords = json.loads(z.coordinates_json)
    except Exception:
        coords = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
    return MonitoringZoneResponse(
        id=z.id,
        camera_id=z.camera_id,
        name=z.name,
        zone_type=z.zone_type,
        coordinates=coords,
        max_occupancy=z.max_occupancy,
        vacancy_alert_minutes=z.vacancy_alert_minutes,
        is_active=z.is_active,
        current_count=z.current_count,
        last_occupied_at=z.last_occupied_at,
    )


def serialize_camera(cam: Camera) -> CameraResponse:
    """Strictly credential-free serialization of Camera."""
    return CameraResponse(
        id=cam.id,
        name=cam.name,
        location=cam.location,
        department_id=cam.department_id,
        department_name=cam.department.name if cam.department else None,
        camera_type=cam.camera_type,
        is_simulated=cam.is_simulated,
        masked_endpoint=cam.masked_endpoint,
        status=cam.status,
        resolution=cam.resolution,
        fps=cam.fps,
        last_heartbeat_at=cam.last_heartbeat_at,
        reconnect_attempts=cam.reconnect_attempts,
        current_occupancy=cam.current_occupancy,
        max_occupancy_threshold=cam.max_occupancy_threshold,
        ai_enabled=cam.ai_enabled,
        recording_enabled=cam.recording_enabled,
        zones=[serialize_zone(z) for z in cam.zones],
    )


@router.get("", response_model=List[CameraResponse])
def list_cameras(
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    cams = db.query(Camera).order_by(Camera.id.asc()).all()
    return [serialize_camera(c) for c in cams]


@router.post("", response_model=CameraResponse, status_code=201)
def create_camera(
    payload: CameraCreate,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    is_sim = payload.is_simulated or payload.camera_type == "simulated"
    if is_sim and not settings.ALLOW_SIMULATED_FEEDS:
        raise HTTPException(
            status_code=400,
            detail="Simulated feeds are disabled in this production environment.",
        )

    masked = mask_stream_endpoint(payload.rtsp_url, is_simulated=is_sim)
    cam = Camera(
        name=payload.name,
        location=payload.location,
        department_id=payload.department_id,
        camera_type="simulated" if is_sim else payload.camera_type,
        is_simulated=is_sim,
        rtsp_url_encrypted=encrypt_secret(payload.rtsp_url) if not is_sim else None,
        username_encrypted=encrypt_secret(payload.username) if not is_sim else None,
        password_encrypted=encrypt_secret(payload.password) if not is_sim else None,
        masked_endpoint=masked,
        status="online" if is_sim else "reconnecting",
        resolution="1280x720",
        fps=15.0,
        last_heartbeat_at=datetime.now(timezone.utc),
        max_occupancy_threshold=payload.max_occupancy_threshold,
        ai_enabled=payload.ai_enabled,
        recording_enabled=payload.recording_enabled,
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)

    log_audit(
        db=db,
        action="camera_added",
        resource_type="camera",
        resource_id=str(cam.id),
        details=f"Added camera '{cam.name}' ({cam.camera_type}, simulated={cam.is_simulated}) at {cam.location}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return serialize_camera(cam)


@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    if payload.name is not None:
        cam.name = payload.name
    if payload.location is not None:
        cam.location = payload.location
    if payload.department_id is not None:
        cam.department_id = payload.department_id
    if payload.rtsp_url is not None and not cam.is_simulated:
        cam.rtsp_url_encrypted = encrypt_secret(payload.rtsp_url)
        cam.masked_endpoint = mask_stream_endpoint(payload.rtsp_url, is_simulated=False)
    if payload.username is not None and not cam.is_simulated:
        cam.username_encrypted = encrypt_secret(payload.username)
    if payload.password is not None and not cam.is_simulated:
        cam.password_encrypted = encrypt_secret(payload.password)
    if payload.max_occupancy_threshold is not None:
        cam.max_occupancy_threshold = payload.max_occupancy_threshold
    if payload.ai_enabled is not None:
        cam.ai_enabled = payload.ai_enabled
    if payload.recording_enabled is not None:
        cam.recording_enabled = payload.recording_enabled
    if payload.status is not None and payload.status in ("online", "offline", "degraded", "reconnecting", "obstructed"):
        cam.status = payload.status

    db.commit()
    db.refresh(cam)

    log_audit(
        db=db,
        action="camera_updated",
        resource_type="camera",
        resource_id=str(cam.id),
        details=f"Updated camera '{cam.name}' configuration.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return serialize_camera(cam)


@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    cname = cam.name
    db.delete(cam)
    db.commit()

    log_audit(
        db=db,
        action="camera_removed",
        resource_type="camera",
        resource_id=str(camera_id),
        details=f"Removed camera '{cname}'.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "deleted", "camera_id": camera_id}


@router.post("/test-connection", response_model=CameraConnectionTestResponse)
def test_new_connection(
    payload: CameraConnectionTestRequest,
    current_user: User = Depends(require_cctv_access),
):
    result = test_camera_connection(
        rtsp_url=payload.rtsp_url,
        username=payload.username,
        password=payload.password,
        is_simulated=payload.is_simulated,
    )
    return CameraConnectionTestResponse(**result)


@router.post("/{camera_id}/test", response_model=CameraConnectionTestResponse)
def test_saved_camera(
    camera_id: int,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    raw_url = decrypt_secret(cam.rtsp_url_encrypted)
    raw_user = decrypt_secret(cam.username_encrypted)
    raw_pass = decrypt_secret(cam.password_encrypted)
    result = test_camera_connection(
        rtsp_url=raw_url,
        username=raw_user,
        password=raw_pass,
        is_simulated=cam.is_simulated,
    )

    cam.last_heartbeat_at = datetime.now(timezone.utc)
    if result["reachable"]:
        cam.status = "online"
        cam.reconnect_attempts = 0
        if result["resolution"]:
            cam.resolution = result["resolution"]
        if result["fps"]:
            cam.fps = result["fps"]
    else:
        cam.status = "offline"
        cam.reconnect_attempts += 1
    db.commit()

    log_audit(
        db=db,
        action="camera_connection_tested",
        resource_type="camera",
        resource_id=str(cam.id),
        details=f"Tested camera '{cam.name}': reachable={result['reachable']}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return CameraConnectionTestResponse(**result)


@router.get("/discover/onvif", response_model=List[OnvifDeviceDiscovered])
def discover_onvif(
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    devices = discover_onvif_cameras(timeout_seconds=1.2)
    log_audit(
        db=db,
        action="onvif_discovery_scan",
        resource_type="camera",
        details=f"ONVIF WS-Discovery returned {len(devices)} device(s).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return [OnvifDeviceDiscovered(**d) for d in devices]


# ==============================================================================
# Monitoring Zones CRUD
# ==============================================================================
@router.post("/{camera_id}/zones", response_model=MonitoringZoneResponse, status_code=201)
def add_monitoring_zone(
    camera_id: int,
    payload: MonitoringZoneCreate,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    zone = MonitoringZone(
        camera_id=cam.id,
        name=payload.name,
        zone_type=payload.zone_type,
        coordinates_json=json.dumps(payload.coordinates),
        max_occupancy=payload.max_occupancy,
        vacancy_alert_minutes=payload.vacancy_alert_minutes,
        is_active=payload.is_active,
        last_occupied_at=datetime.now(timezone.utc),
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    log_audit(
        db=db,
        action="monitoring_zone_created",
        resource_type="monitoring_zone",
        resource_id=str(zone.id),
        details=f"Created {zone.zone_type} zone '{zone.name}' on camera '{cam.name}'.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return serialize_zone(zone)


@router.delete("/{camera_id}/zones/{zone_id}")
def delete_monitoring_zone(
    camera_id: int,
    zone_id: int,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    zone = (
        db.query(MonitoringZone)
        .filter(MonitoringZone.id == zone_id, MonitoringZone.camera_id == camera_id)
        .first()
    )
    if not zone:
        raise HTTPException(status_code=404, detail="Monitoring zone not found.")
    zname = zone.name
    db.delete(zone)
    db.commit()

    log_audit(
        db=db,
        action="monitoring_zone_deleted",
        resource_type="monitoring_zone",
        resource_id=str(zone_id),
        details=f"Deleted zone '{zname}' from camera #{camera_id}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "deleted", "zone_id": zone_id}


# ==============================================================================
# Authorized Live Video Streaming (Signed Token + Audit Trail)
# ==============================================================================
@router.post("/{camera_id}/stream-token")
def issue_stream_token(
    camera_id: int,
    request: Request,
    current_user: User = Depends(require_cctv_access),
    db: Session = Depends(get_db),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    token = create_stream_token(user_id=current_user.id, camera_id=cam.id, role=current_user.role)
    log_audit(
        db=db,
        action="cctv_live_stream_accessed",
        resource_type="camera",
        resource_id=str(cam.id),
        details=f"Issued short-lived live view token for '{cam.name}' (simulated={cam.is_simulated}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return {
        "stream_token": token,
        "stream_url": f"/api/cameras/{cam.id}/stream?token={token}",
        "snapshot_url": f"/api/cameras/{cam.id}/snapshot?token={token}",
        "is_simulated": cam.is_simulated,
    }


def _validate_stream_token(token: str, camera_id: int, db: Session) -> User:
    payload = decode_token(token)
    if (
        not payload
        or payload.get("type") != "stream"
        or payload.get("camera_id") != camera_id
        or payload.get("role") not in (ROLE_SUPER_ADMIN, ROLE_HR_ADMIN)
    ):
        raise HTTPException(status_code=403, detail="Invalid or unauthorized stream token.")
    user = db.query(User).filter(User.id == int(payload["sub"]), User.can_view_cctv == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=403, detail="User is not authorized to view CCTV streams.")
    return user


@router.get("/{camera_id}/snapshot")
def camera_snapshot(
    camera_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Single authorized JPEG frame snapshot (useful for low-bandwidth thumbnails)."""
    _validate_stream_token(token, camera_id, db)
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    zones_payload = [
        {"name": z.name, "zone_type": z.zone_type, "coordinates": z.coordinates_json}
        for z in cam.zones
        if z.is_active
    ]

    if cam.is_simulated:
        frame_bytes, _ = simulator_feed.generate_frame_jpeg(
            camera_id=cam.id,
            camera_name=cam.name,
            location=cam.location,
            occupancy=cam.current_occupancy,
            zones=zones_payload,
            status=cam.status,
        )
    else:
        frame_bytes = stream_manager.capture_single_rtsp_frame(
            camera_id=cam.id,
            rtsp_url_encrypted=cam.rtsp_url_encrypted,
            username_encrypted=cam.username_encrypted,
            password_encrypted=cam.password_encrypted,
        )
        if frame_bytes is None:
            frame_bytes, _ = simulator_feed.generate_frame_jpeg(
                camera_id=cam.id,
                camera_name=f"{cam.name} [RTSP Offline]",
                location=cam.location,
                occupancy=0,
                zones=[],
                status="offline",
            )

    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get("/{camera_id}/stream")
async def camera_mjpeg_stream(
    camera_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Authorized multipart MJPEG live video stream."""
    _validate_stream_token(token, camera_id, db)
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    zones_payload = [
        {"name": z.name, "zone_type": z.zone_type, "coordinates": z.coordinates_json}
        for z in cam.zones
        if z.is_active
    ]

    # Snapshot camera metadata before releasing DB session inside generator
    cam_id = cam.id
    cam_name = cam.name
    cam_location = cam.location
    cam_sim = cam.is_simulated
    cam_occ = cam.current_occupancy
    cam_status = cam.status
    rtsp_enc = cam.rtsp_url_encrypted
    user_enc = cam.username_encrypted
    pass_enc = cam.password_encrypted

    return StreamingResponse(
        stream_manager.mjpeg_stream_generator(
            camera_id=cam_id,
            camera_name=cam_name,
            location=cam_location,
            is_simulated=cam_sim,
            occupancy=cam_occ,
            zones=zones_payload,
            status=cam_status,
            rtsp_url_encrypted=rtsp_enc,
            username_encrypted=user_enc,
            password_encrypted=pass_enc,
            fps=3.0,
        ),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
