"""Authentication, Session Profile, and Transparent Monitoring Consent Endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.models import Department, Employee, RetentionPolicy, User
from app.schemas.schemas import (
    ConsentUpdateRequest,
    LoginRequest,
    TokenResponse,
    UserProfile,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def build_user_profile(db: Session, user: User) -> UserProfile:
    managed_dept_name = None
    if user.managed_department_id:
        md = db.query(Department).filter(Department.id == user.managed_department_id).first()
        managed_dept_name = md.name if md else None

    emp_code = None
    dept_id = None
    dept_name = None
    consent_acc = None
    consent_at = None
    if user.employee_id:
        emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if emp:
            emp_code = emp.employee_code
            dept_id = emp.department_id
            dept_name = emp.department.name if emp.department else None
            consent_acc = emp.privacy_consent_accepted
            consent_at = emp.privacy_consent_at

    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        can_view_cctv=user.can_view_cctv,
        managed_department_id=user.managed_department_id,
        managed_department_name=managed_dept_name,
        employee_id=user.employee_id,
        employee_code=emp_code,
        department_id=dept_id,
        department_name=dept_name,
        privacy_consent_accepted=consent_acc,
        privacy_consent_at=consent_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        extra_claims={
            "email": user.email,
            "can_view_cctv": user.can_view_cctv,
            "managed_department_id": user.managed_department_id,
        },
    )

    log_audit(
        db=db,
        action="user_login",
        resource_type="user",
        resource_id=str(user.id),
        details=f"Authenticated portal session as {user.role}.",
        user=user,
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(access_token=token, user=build_user_profile(db, user))


@router.get("/me", response_model=UserProfile)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_user_profile(db, current_user)


@router.get("/monitoring-policy")
def get_monitoring_policy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accessible to all authenticated roles (including Employees) for full transparency."""
    policy = db.query(RetentionPolicy).first()
    return {
        "version": policy.monitoring_notice_version if policy else "2026.1",
        "notice_text": policy.monitoring_notice_text if policy else "",
        "video_retention_days": policy.video_retention_days if policy else 7,
        "event_metadata_retention_days": policy.event_metadata_retention_days if policy else 90,
        "raw_video_storage_enabled": policy.enable_raw_video_storage if policy else False,
        "prohibited_practices": [
            "No facial recognition or biometric identification",
            "No emotion or mood recognition",
            "No covert or undisclosed monitoring",
            "No automated employee productivity scoring",
            "No automated disciplinary or employment decisions",
        ],
    }


@router.post("/consent")
def update_privacy_consent(
    payload: ConsentUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="No employee profile linked to this account.")

    emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee profile not found.")

    emp.privacy_consent_accepted = payload.accepted
    emp.privacy_consent_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(
        db=db,
        action="privacy_consent_updated",
        resource_type="employee",
        resource_id=str(emp.id),
        details=f"Employee monitoring disclosure acknowledgment set to {payload.accepted}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return {
        "privacy_consent_accepted": emp.privacy_consent_accepted,
        "privacy_consent_at": emp.privacy_consent_at,
    }
