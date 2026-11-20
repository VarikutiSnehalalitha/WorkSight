"""Real-Time Notifications & Human Review Endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import ALL_ROLES, ROLE_DEPT_MANAGER, ROLE_EMPLOYEE, require_roles
from app.core.database import get_db
from app.models.models import Notification, User
from app.schemas.schemas import NotificationResponse, NotificationReviewRequest
from app.services.audit import log_audit

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(default=False),
    category: Optional[str] = Query(default=None),
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    q = db.query(Notification)
    if unread_only:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    if category:
        q = q.filter(Notification.category == category)

    all_items = q.order_by(Notification.created_at.desc()).limit(150).all()

    filtered: List[Notification] = []
    for n in all_items:
        if n.target_user_id is not None:
            if n.target_user_id == current_user.id:
                filtered.append(n)
            continue
        roles = {r.strip() for r in n.target_roles.split(",") if r.strip()}
        if current_user.role not in roles:
            continue
        if (
            current_user.role == ROLE_DEPT_MANAGER
            and n.department_id is not None
            and n.department_id != current_user.managed_department_id
        ):
            continue
        if current_user.role == ROLE_EMPLOYEE and n.target_user_id != current_user.id:
            continue
        filtered.append(n)

    return filtered


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    payload: NotificationReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if current_user.role == ROLE_EMPLOYEE and n.target_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify another user's notification.")

    if payload.is_read is not None:
        n.is_read = payload.is_read
    if payload.review_status is not None:
        n.review_status = payload.review_status
        n.is_read = True
        n.reviewed_by_user_id = current_user.id
    if payload.review_notes is not None:
        n.review_notes = payload.review_notes

    db.commit()
    db.refresh(n)

    if payload.review_status:
        log_audit(
            db=db,
            action=f"notification_{payload.review_status}",
            resource_type="notification",
            resource_id=str(n.id),
            details=f"Updated alert '{n.title}' to {payload.review_status}.",
            user=current_user,
            ip_address=request.client.host if request.client else None,
        )
    return n


@router.post("/mark-all-read")
def mark_all_read(
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    notifs = list_notifications(
        unread_only=True,
        category=None,
        current_user=current_user,
        db=db,
    )
    for n in notifs:
        n.is_read = True
    db.commit()
    return {"marked_read": len(notifs)}
