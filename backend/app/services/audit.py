"""Centralized Access Audit Trail Service."""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog, User


def log_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    user: Optional[User] = None,
    ip_address: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else "system",
        user_role=user.role if user else "system",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
