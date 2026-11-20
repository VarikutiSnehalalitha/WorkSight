"""Leave Application & HR/Manager Approval Workflow Endpoints."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    ALL_ROLES,
    MANAGEMENT_ROLES,
    ROLE_DEPT_MANAGER,
    ROLE_EMPLOYEE,
    require_roles,
)
from app.core.database import get_db
from app.models.models import AttendanceRecord, Employee, LeaveRequest, Notification, User
from app.schemas.schemas import LeaveCreateRequest, LeaveResponse, LeaveReviewRequest
from app.services.audit import log_audit
from app.services.realtime import realtime_hub

router = APIRouter(prefix="/api/leaves", tags=["Leave Management"])


def _serialize_leave(lr: LeaveRequest) -> LeaveResponse:
    emp = lr.employee
    return LeaveResponse(
        id=lr.id,
        employee_id=lr.employee_id,
        employee_name=emp.full_name if emp else "Unknown",
        employee_code=emp.employee_code if emp else "-",
        department_id=emp.department_id if emp else 0,
        department_name=emp.department.name if (emp and emp.department) else "Unassigned",
        leave_type=lr.leave_type,
        start_date=lr.start_date,
        end_date=lr.end_date,
        days_count=lr.days_count,
        reason=lr.reason,
        status=lr.status,
        reviewed_by_name=lr.reviewer.full_name if lr.reviewer else None,
        review_notes=lr.review_notes,
        reviewed_at=lr.reviewed_at,
        created_at=lr.created_at,
    )


@router.get("", response_model=List[LeaveResponse])
def list_leaves(
    status_filter: Optional[str] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    q = db.query(LeaveRequest).join(Employee)
    if current_user.role == ROLE_EMPLOYEE:
        if not current_user.employee_id:
            return []
        q = q.filter(LeaveRequest.employee_id == current_user.employee_id)
    elif current_user.role == ROLE_DEPT_MANAGER:
        q = q.filter(Employee.department_id == current_user.managed_department_id)
    elif department_id is not None:
        q = q.filter(Employee.department_id == department_id)

    if status_filter:
        q = q.filter(LeaveRequest.status == status_filter)

    items = q.order_by(LeaveRequest.created_at.desc()).all()
    return [_serialize_leave(i) for i in items]


@router.post("", response_model=LeaveResponse, status_code=201)
async def apply_leave(
    payload: LeaveCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="No employee profile linked to this account.")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="End date cannot be earlier than start date.")

    emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    days = (payload.end_date - payload.start_date).days + 1
    lr = LeaveRequest(
        employee_id=emp.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days_count=days,
        reason=payload.reason,
        status="pending",
    )
    db.add(lr)
    db.flush()

    notif = Notification(
        title=f"New Leave Application — {emp.full_name}",
        message=f"{payload.leave_type.title()} leave requested for {payload.start_date} to {payload.end_date} ({days} day(s)).",
        category="leave",
        severity="info",
        target_roles="super_admin,hr_admin,dept_manager",
        department_id=emp.department_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(lr)

    log_audit(
        db=db,
        action="leave_applied",
        resource_type="leave_request",
        resource_id=str(lr.id),
        details=f"{emp.full_name} applied for {days}d {payload.leave_type} leave.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )

    await realtime_hub.broadcast(
        event_type="notification",
        payload={"title": notif.title, "category": "leave", "severity": "info"},
        allowed_roles={"super_admin", "hr_admin", "dept_manager"},
        department_id=emp.department_id,
    )

    return _serialize_leave(lr)


@router.post("/{leave_id}/review", response_model=LeaveResponse)
def review_leave(
    leave_id: int,
    payload: LeaveReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    lr = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not lr:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    emp = lr.employee
    if current_user.role == ROLE_DEPT_MANAGER and emp.department_id != current_user.managed_department_id:
        raise HTTPException(status_code=403, detail="Cannot review leave requests outside your department.")

    lr.status = payload.status
    lr.review_notes = payload.review_notes
    lr.reviewed_by_user_id = current_user.id
    lr.reviewed_at = datetime.now(timezone.utc)

    # Mark verified attendance days as on_leave when approved
    if payload.status == "approved":
        cur = lr.start_date
        while cur <= lr.end_date:
            existing = (
                db.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.employee_id == lr.employee_id,
                    AttendanceRecord.attendance_date == cur,
                )
                .first()
            )
            if existing:
                existing.status = "on_leave"
                existing.notes = f"Approved {lr.leave_type} leave"
            else:
                db.add(
                    AttendanceRecord(
                        employee_id=lr.employee_id,
                        attendance_date=cur,
                        verification_method="hr_adjusted",
                        record_category="verified_attendance",
                        status="on_leave",
                        working_hours=0.0,
                        notes=f"Approved {lr.leave_type} leave",
                    )
                )
            cur += timedelta(days=1)

    if emp.user_account:
        db.add(
            Notification(
                title=f"Leave Request {payload.status.title()}",
                message=f"Your {lr.leave_type} leave ({lr.start_date} to {lr.end_date}) was {payload.status}.",
                category="leave",
                severity="info",
                target_roles="employee",
                target_user_id=emp.user_account.id,
            )
        )

    db.commit()
    db.refresh(lr)

    log_audit(
        db=db,
        action=f"leave_{payload.status}",
        resource_type="leave_request",
        resource_id=str(lr.id),
        details=f"{payload.status.title()} {lr.leave_type} leave for {emp.full_name}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return _serialize_leave(lr)
