"""Privacy, Retention Policies, Role-Based CCTV Permissions & Access Audit Trail."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_AND_HR, ROLE_SUPER_ADMIN, require_roles
from app.core.database import get_db
from app.models.models import AuditLog, RetentionPolicy, User
from app.schemas.schemas import (
    AuditLogResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
)
from app.services.audit import log_audit
from app.services.retention import run_retention_purge

router = APIRouter(prefix="/api/settings", tags=["Privacy & Governance Settings"])


class UserAccessToggleRequest(BaseModel):
    can_view_cctv: bool


@router.get("/retention", response_model=RetentionPolicyResponse)
def get_retention_policy(
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    policy = db.query(RetentionPolicy).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Retention policy not initialized.")
    return policy


@router.put("/retention", response_model=RetentionPolicyResponse)
def update_retention_policy(
    payload: RetentionPolicyUpdate,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    policy = db.query(RetentionPolicy).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Retention policy not initialized.")

    if payload.video_retention_days is not None:
        policy.video_retention_days = payload.video_retention_days
    if payload.event_metadata_retention_days is not None:
        policy.event_metadata_retention_days = payload.event_metadata_retention_days
    if payload.enable_raw_video_storage is not None:
        policy.enable_raw_video_storage = payload.enable_raw_video_storage
    if payload.auto_purge_enabled is not None:
        policy.auto_purge_enabled = payload.auto_purge_enabled
    if payload.monitoring_notice_text is not None:
        policy.monitoring_notice_text = payload.monitoring_notice_text

    policy.updated_by_user_id = current_user.id
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)

    log_audit(
        db=db,
        action="retention_policy_updated",
        resource_type="retention_policy",
        resource_id=str(policy.id),
        details=(
            f"Updated retention: video={policy.video_retention_days}d, "
            f"events={policy.event_metadata_retention_days}d, "
            f"raw_video={policy.enable_raw_video_storage}."
        ),
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return policy


@router.post("/run-retention")
def trigger_retention_purge(
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    return run_retention_purge(db, triggered_by=current_user)


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=300),
    action: str = Query(default=""),
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/user-access")
def list_user_access_controls(
    current_user: User = Depends(require_roles([ROLE_SUPER_ADMIN])),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "can_view_cctv": u.can_view_cctv,
            "is_active": u.is_active,
            "last_login_at": u.last_login_at,
        }
        for u in users
    ]


@router.patch("/user-access/{user_id}")
def update_user_cctv_access(
    user_id: int,
    payload: UserAccessToggleRequest,
    request: Request,
    current_user: User = Depends(require_roles([ROLE_SUPER_ADMIN])),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.role not in ("super_admin", "hr_admin") and payload.can_view_cctv:
        raise HTTPException(
            status_code=400,
            detail="Privacy guardrail: Only Super Admin or HR Admin accounts may hold live CCTV viewing privileges.",
        )

    target.can_view_cctv = payload.can_view_cctv
    db.commit()

    log_audit(
        db=db,
        action="cctv_permission_changed",
        resource_type="user",
        resource_id=str(target.id),
        details=f"Set can_view_cctv={payload.can_view_cctv} for {target.email}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return {"id": target.id, "email": target.email, "can_view_cctv": target.can_view_cctv}
