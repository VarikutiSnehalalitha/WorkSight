"""Verified Attendance Management, Shifts, and HR Correction Approval Workflow.

All records in this module represent verified individual attendance (access card,
QR check-in, web portal, or HR-approved adjustment), strictly distinct from
anonymous AI presence telemetry.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_AND_HR,
    ALL_ROLES,
    MANAGEMENT_ROLES,
    ROLE_DEPT_MANAGER,
    ROLE_EMPLOYEE,
    get_current_user,
    require_roles,
    resolve_department_scope,
)
from app.core.database import get_db
from app.models.models import (
    AttendanceCorrection,
    AttendanceRecord,
    Employee,
    Notification,
    Shift,
    User,
)
from app.schemas.schemas import (
    AttendanceRecordResponse,
    CheckInOutRequest,
    CorrectionCreateRequest,
    CorrectionResponse,
    CorrectionReviewRequest,
    ShiftCreate,
    ShiftResponse,
)
from app.services.audit import log_audit
from app.services.realtime import realtime_hub

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


def _serialize_record(rec: AttendanceRecord) -> AttendanceRecordResponse:
    emp = rec.employee
    return AttendanceRecordResponse(
        id=rec.id,
        employee_id=rec.employee_id,
        employee_name=emp.full_name if emp else "Unknown",
        employee_code=emp.employee_code if emp else "-",
        department_id=emp.department_id if emp else 0,
        department_name=emp.department.name if (emp and emp.department) else "Unassigned",
        attendance_date=rec.attendance_date,
        check_in_time=rec.check_in_time,
        check_out_time=rec.check_out_time,
        verification_method=rec.verification_method,
        record_category=rec.record_category,
        status=rec.status,
        working_hours=rec.working_hours,
        late_minutes=rec.late_minutes,
        early_departure_minutes=rec.early_departure_minutes,
        notes=rec.notes,
        is_corrected=rec.is_corrected,
    )


def _serialize_correction(c: AttendanceCorrection) -> CorrectionResponse:
    emp = c.employee
    return CorrectionResponse(
        id=c.id,
        employee_id=c.employee_id,
        employee_name=emp.full_name if emp else "Unknown",
        employee_code=emp.employee_code if emp else "-",
        department_name=emp.department.name if (emp and emp.department) else "Unassigned",
        attendance_record_id=c.attendance_record_id,
        attendance_date=c.attendance_date,
        requested_check_in=c.requested_check_in,
        requested_check_out=c.requested_check_out,
        reason=c.reason,
        status=c.status,
        reviewed_by_name=c.reviewer.full_name if c.reviewer else None,
        review_notes=c.review_notes,
        reviewed_at=c.reviewed_at,
        created_at=c.created_at,
    )


def _evaluate_shift_timings(
    shift: Optional[Shift],
    att_date: date,
    check_in: Optional[datetime],
    check_out: Optional[datetime],
):
    late_minutes = 0
    early_minutes = 0
    working_hours = 0.0

    start_h, start_m = (9, 0)
    end_h, end_m = (17, 30)
    grace = 15
    early_thresh = 15
    if shift:
        start_h, start_m = map(int, shift.start_time.split(":"))
        end_h, end_m = map(int, shift.end_time.split(":"))
        grace = shift.grace_period_minutes
        early_thresh = shift.early_departure_threshold_minutes

    shift_start = datetime.combine(att_date, time(start_h, start_m), tzinfo=timezone.utc)
    shift_end = datetime.combine(att_date, time(end_h, end_m), tzinfo=timezone.utc)

    if check_in:
        ci = check_in if check_in.tzinfo else check_in.replace(tzinfo=timezone.utc)
        diff_in = int((ci - shift_start).total_seconds() // 60)
        if diff_in > grace:
            late_minutes = diff_in

    if check_out:
        co = check_out if check_out.tzinfo else check_out.replace(tzinfo=timezone.utc)
        diff_out = int((shift_end - co).total_seconds() // 60)
        if diff_out > early_thresh:
            early_minutes = diff_out
        if check_in:
            ci = check_in if check_in.tzinfo else check_in.replace(tzinfo=timezone.utc)
            working_hours = round(max(0.0, (co - ci).total_seconds() / 3600.0), 2)

    if late_minutes > 0 and early_minutes > 0:
        status = "late_and_early"
    elif late_minutes > 0:
        status = "late"
    elif early_minutes > 0:
        status = "early_departure"
    else:
        status = "present"

    return status, working_hours, late_minutes, early_minutes


@router.get("", response_model=List[AttendanceRecordResponse])
def list_attendance(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    employee_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    q = db.query(AttendanceRecord).join(Employee)

    if current_user.role == ROLE_EMPLOYEE:
        if not current_user.employee_id:
            return []
        q = q.filter(AttendanceRecord.employee_id == current_user.employee_id)
    else:
        scoped_dept = resolve_department_scope(current_user, department_id)
        if scoped_dept is not None:
            q = q.filter(Employee.department_id == scoped_dept)
        if employee_id is not None:
            q = q.filter(AttendanceRecord.employee_id == employee_id)

    if start_date:
        q = q.filter(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        q = q.filter(AttendanceRecord.attendance_date <= end_date)
    if status_filter:
        q = q.filter(AttendanceRecord.status == status_filter)

    records = (
        q.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.check_in_time.desc())
        .limit(300)
        .all()
    )
    return [_serialize_record(r) for r in records]


@router.post("/check-in", response_model=AttendanceRecordResponse)
async def check_in(
    payload: CheckInOutRequest,
    request: Request,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    if current_user.role == ROLE_EMPLOYEE:
        emp_id = current_user.employee_id
    else:
        emp_id = payload.employee_id or current_user.employee_id

    if not emp_id:
        raise HTTPException(status_code=400, detail="No employee specified for check-in.")

    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    if current_user.role == ROLE_DEPT_MANAGER and emp.department_id != current_user.managed_department_id:
        raise HTTPException(status_code=403, detail="Cannot check in employee outside your department.")

    if payload.verification_method not in ("access_card", "qr_code", "web_portal"):
        raise HTTPException(status_code=400, detail="Unsupported verification method.")

    today = date.today()
    now = datetime.now(timezone.utc)
    rec = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.attendance_date == today,
        )
        .first()
    )

    if rec and rec.check_in_time is not None and rec.status not in ("absent",):
        raise HTTPException(status_code=400, detail="Verified check-in already recorded for today.")

    status, working_hours, late_min, early_min = _evaluate_shift_timings(emp.shift, today, now, None)

    if rec:
        rec.check_in_time = now
        rec.verification_method = payload.verification_method
        rec.status = status
        rec.late_minutes = late_min
        rec.notes = payload.notes
    else:
        rec = AttendanceRecord(
            employee_id=emp.id,
            attendance_date=today,
            check_in_time=now,
            verification_method=payload.verification_method,
            record_category="verified_attendance",
            status=status,
            working_hours=working_hours,
            late_minutes=late_min,
            early_departure_minutes=early_min,
            notes=payload.notes,
        )
        db.add(rec)

    db.commit()
    db.refresh(rec)

    log_audit(
        db=db,
        action="verified_check_in",
        resource_type="attendance_record",
        resource_id=str(rec.id),
        details=f"{emp.full_name} checked in via {payload.verification_method} (status={rec.status}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )

    await realtime_hub.broadcast(
        event_type="attendance_update",
        payload={
            "action": "check_in",
            "employee_name": emp.full_name,
            "department_id": emp.department_id,
            "status": rec.status,
            "verification_method": rec.verification_method,
        },
        allowed_roles={"super_admin", "hr_admin", "dept_manager"},
        department_id=emp.department_id,
    )

    return _serialize_record(rec)


@router.post("/check-out", response_model=AttendanceRecordResponse)
async def check_out(
    payload: CheckInOutRequest,
    request: Request,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    if current_user.role == ROLE_EMPLOYEE:
        emp_id = current_user.employee_id
    else:
        emp_id = payload.employee_id or current_user.employee_id

    if not emp_id:
        raise HTTPException(status_code=400, detail="No employee specified for check-out.")

    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    today = date.today()
    now = datetime.now(timezone.utc)
    rec = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.attendance_date == today,
        )
        .first()
    )
    if not rec or not rec.check_in_time:
        raise HTTPException(status_code=400, detail="No verified check-in found for today.")

    status, working_hours, late_min, early_min = _evaluate_shift_timings(
        emp.shift, today, rec.check_in_time, now
    )
    rec.check_out_time = now
    rec.status = status
    rec.working_hours = working_hours
    rec.late_minutes = late_min
    rec.early_departure_minutes = early_min
    if payload.notes:
        rec.notes = payload.notes

    db.commit()
    db.refresh(rec)

    log_audit(
        db=db,
        action="verified_check_out",
        resource_type="attendance_record",
        resource_id=str(rec.id),
        details=f"{emp.full_name} checked out ({working_hours}h worked, status={status}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )

    await realtime_hub.broadcast(
        event_type="attendance_update",
        payload={
            "action": "check_out",
            "employee_name": emp.full_name,
            "department_id": emp.department_id,
            "working_hours": working_hours,
        },
        allowed_roles={"super_admin", "hr_admin", "dept_manager"},
        department_id=emp.department_id,
    )

    return _serialize_record(rec)


# ==============================================================================
# Shifts
# ==============================================================================
@router.get("/shifts", response_model=List[ShiftResponse])
def list_shifts(
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    return db.query(Shift).order_by(Shift.id.asc()).all()


@router.post("/shifts", response_model=ShiftResponse, status_code=201)
def create_shift(
    payload: ShiftCreate,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    if db.query(Shift).filter(Shift.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Shift name already exists.")
    if payload.is_default:
        db.query(Shift).update({Shift.is_default: False})
    sh = Shift(
        name=payload.name,
        start_time=payload.start_time,
        end_time=payload.end_time,
        grace_period_minutes=payload.grace_period_minutes,
        early_departure_threshold_minutes=payload.early_departure_threshold_minutes,
        is_default=payload.is_default,
    )
    db.add(sh)
    db.commit()
    db.refresh(sh)
    log_audit(
        db=db,
        action="shift_created",
        resource_type="shift",
        resource_id=str(sh.id),
        details=f"Created shift {sh.name} ({sh.start_time}-{sh.end_time}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return sh


# ==============================================================================
# Attendance Correction Requests & HR Approval Workflow
# ==============================================================================
@router.get("/corrections", response_model=List[CorrectionResponse])
def list_corrections(
    status_filter: Optional[str] = Query(default=None),
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    q = db.query(AttendanceCorrection).join(Employee)
    if current_user.role == ROLE_EMPLOYEE:
        if not current_user.employee_id:
            return []
        q = q.filter(AttendanceCorrection.employee_id == current_user.employee_id)
    elif current_user.role == ROLE_DEPT_MANAGER:
        q = q.filter(Employee.department_id == current_user.managed_department_id)

    if status_filter:
        q = q.filter(AttendanceCorrection.status == status_filter)

    items = q.order_by(AttendanceCorrection.created_at.desc()).all()
    return [_serialize_correction(c) for c in items]


@router.post("/corrections", response_model=CorrectionResponse, status_code=201)
async def create_correction_request(
    payload: CorrectionCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="No employee profile linked to this user.")

    emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    corr = AttendanceCorrection(
        employee_id=emp.id,
        attendance_record_id=payload.attendance_record_id,
        attendance_date=payload.attendance_date,
        requested_check_in=payload.requested_check_in,
        requested_check_out=payload.requested_check_out,
        reason=payload.reason,
        status="pending",
    )
    db.add(corr)
    db.flush()

    notif = Notification(
        title=f"Attendance Correction Request — {emp.full_name}",
        message=f"Requested adjustment for {payload.attendance_date.isoformat()}: {payload.reason[:120]}",
        category="attendance",
        severity="info",
        target_roles="super_admin,hr_admin,dept_manager",
        department_id=emp.department_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(corr)

    log_audit(
        db=db,
        action="attendance_correction_submitted",
        resource_type="attendance_correction",
        resource_id=str(corr.id),
        details=f"{emp.full_name} submitted correction for {payload.attendance_date}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )

    await realtime_hub.broadcast(
        event_type="notification",
        payload={"title": notif.title, "category": "attendance", "severity": "info"},
        allowed_roles={"super_admin", "hr_admin", "dept_manager"},
        department_id=emp.department_id,
    )

    return _serialize_correction(corr)


@router.post("/corrections/{correction_id}/review", response_model=CorrectionResponse)
def review_correction(
    correction_id: int,
    payload: CorrectionReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    corr = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == correction_id).first()
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found.")

    emp = corr.employee
    if current_user.role == ROLE_DEPT_MANAGER and emp.department_id != current_user.managed_department_id:
        raise HTTPException(status_code=403, detail="Cannot review correction requests outside your department.")

    corr.status = payload.status
    corr.review_notes = payload.review_notes
    corr.reviewed_by_user_id = current_user.id
    corr.reviewed_at = datetime.now(timezone.utc)

    # Apply approved correction to verified AttendanceRecord
    if payload.status == "approved":
        rec = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.employee_id == corr.employee_id,
                AttendanceRecord.attendance_date == corr.attendance_date,
            )
            .first()
        )
        ci_dt = rec.check_in_time if rec else None
        co_dt = rec.check_out_time if rec else None

        if corr.requested_check_in:
            h, m = map(int, corr.requested_check_in.split(":"))
            ci_dt = datetime.combine(corr.attendance_date, time(h, m), tzinfo=timezone.utc)
        if corr.requested_check_out:
            h, m = map(int, corr.requested_check_out.split(":"))
            co_dt = datetime.combine(corr.attendance_date, time(h, m), tzinfo=timezone.utc)

        new_status, hrs, late_m, early_m = _evaluate_shift_timings(
            emp.shift, corr.attendance_date, ci_dt, co_dt
        )

        if rec:
            rec.check_in_time = ci_dt
            rec.check_out_time = co_dt
            rec.status = new_status
            rec.working_hours = hrs
            rec.late_minutes = late_m
            rec.early_departure_minutes = early_m
            rec.is_corrected = True
            rec.verification_method = "hr_adjusted"
            rec.notes = f"HR Corrected: {payload.review_notes or corr.reason}"
        else:
            rec = AttendanceRecord(
                employee_id=corr.employee_id,
                attendance_date=corr.attendance_date,
                check_in_time=ci_dt,
                check_out_time=co_dt,
                verification_method="hr_adjusted",
                record_category="verified_attendance",
                status=new_status,
                working_hours=hrs,
                late_minutes=late_m,
                early_departure_minutes=early_m,
                is_corrected=True,
                notes=f"HR Corrected: {payload.review_notes or corr.reason}",
            )
            db.add(rec)

    # Notify employee of decision
    if emp.user_account:
        db.add(
            Notification(
                title=f"Attendance Correction {payload.status.title()}",
                message=f"Your correction for {corr.attendance_date.isoformat()} was {payload.status}. {payload.review_notes or ''}".strip(),
                category="attendance",
                severity="info",
                target_roles="employee",
                target_user_id=emp.user_account.id,
            )
        )

    db.commit()
    db.refresh(corr)

    log_audit(
        db=db,
        action=f"attendance_correction_{payload.status}",
        resource_type="attendance_correction",
        resource_id=str(corr.id),
        details=f"Reviewed correction for {emp.full_name} ({corr.attendance_date}): {payload.status}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return _serialize_correction(corr)
