"""Executive Admin/HR/Manager Dashboard & Employee Self-Service Overview Endpoints."""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai_vision.detector import person_detector
from app.api.cameras import serialize_camera
from app.api.departments import compute_department_metrics
from app.api.deps import (
    ALL_ROLES,
    MANAGEMENT_ROLES,
    ROLE_DEPT_MANAGER,
    require_roles,
    resolve_department_scope,
)
from app.api.events import serialize_vision_event
from app.core.database import get_db
from app.models.models import (
    AttendanceCorrection,
    AttendanceRecord,
    Camera,
    Department,
    Employee,
    LeaveRequest,
    RetentionPolicy,
    User,
    VisionEvent,
)
from app.schemas.schemas import AttendanceTrendPoint, DashboardOverviewResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_admin_overview(
    target_date: Optional[date] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    trend_days: int = Query(default=10, ge=5, le=30),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    """Executive & HR/Manager Dashboard. Strictly forbidden for Employee role (403)."""
    dt = target_date or date.today()
    scoped_dept = resolve_department_scope(current_user, department_id)

    emp_q = db.query(Employee).filter(Employee.employment_status != "inactive")
    if scoped_dept is not None:
        emp_q = emp_q.filter(Employee.department_id == scoped_dept)
    employees = emp_q.all()
    emp_ids = [e.id for e in employees]
    total_employees = len(emp_ids)

    currently_present = absent_today = on_leave_today = late_arrivals = early_departures = 0
    if emp_ids:
        recs = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.attendance_date == dt,
            )
            .all()
        )
        rec_map = {r.employee_id: r for r in recs}
        for eid in emp_ids:
            r = rec_map.get(eid)
            if not r or r.status == "absent":
                absent_today += 1
            elif r.status == "on_leave":
                on_leave_today += 1
            else:
                currently_present += 1
                if r.status in ("late", "late_and_early"):
                    late_arrivals += 1
                if r.status in ("early_departure", "late_and_early"):
                    early_departures += 1

    # Department breakdown
    dept_q = db.query(Department)
    if scoped_dept is not None:
        dept_q = dept_q.filter(Department.id == scoped_dept)
    depts = dept_q.order_by(Department.name.asc()).all()
    dept_metrics = [compute_department_metrics(db, d, dt) for d in depts]
    office_capacity = sum(d.target_capacity for d in depts) or 1

    # Cameras & AI Occupancy
    cam_q = db.query(Camera)
    if scoped_dept is not None:
        cam_q = cam_q.filter(Camera.department_id == scoped_dept)
    cams = cam_q.order_by(Camera.id.asc()).all()
    cameras_total = len(cams)
    cameras_online = sum(1 for c in cams if c.status == "online")
    office_occupancy_count = sum(c.current_occupancy for c in cams if c.status == "online")
    office_occupancy_percent = round(
        min(100.0, (office_occupancy_count / office_capacity) * 100.0), 1
    )

    # Pending queues
    leave_q = db.query(LeaveRequest).join(Employee).filter(LeaveRequest.status == "pending")
    corr_q = db.query(AttendanceCorrection).join(Employee).filter(AttendanceCorrection.status == "pending")
    ev_q = db.query(VisionEvent).join(Camera)
    if scoped_dept is not None:
        leave_q = leave_q.filter(Employee.department_id == scoped_dept)
        corr_q = corr_q.filter(Employee.department_id == scoped_dept)
        ev_q = ev_q.filter(Camera.department_id == scoped_dept)

    pending_leaves = leave_q.count()
    pending_corrections = corr_q.count()
    unreviewed_alerts = ev_q.filter(VisionEvent.review_status == "unreviewed").count()
    recent_events = ev_q.order_by(VisionEvent.occurred_at.desc()).limit(8).all()

    # Attendance Trends
    trends: List[AttendanceTrendPoint] = []
    for offset in range(trend_days - 1, -1, -1):
        day = dt - timedelta(days=offset)
        day_recs = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.employee_id.in_(emp_ids) if emp_ids else False,
                AttendanceRecord.attendance_date == day,
            )
            .all()
            if emp_ids
            else []
        )
        p_cnt = sum(1 for r in day_recs if r.status in ("present", "early_departure"))
        l_cnt = sum(1 for r in day_recs if r.status in ("late", "late_and_early"))
        lv_cnt = sum(1 for r in day_recs if r.status == "on_leave")
        ab_cnt = sum(1 for r in day_recs if r.status == "absent")
        peak_occ = max(0, p_cnt + l_cnt - 2) if (p_cnt + l_cnt) > 0 else 0
        trends.append(
            AttendanceTrendPoint(
                date=day.isoformat(),
                present=p_cnt + l_cnt,
                late=l_cnt,
                absent=ab_cnt,
                on_leave=lv_cnt,
                ai_peak_occupancy=peak_occ,
            )
        )

    # Only serialize cameras list for roles with camera summary visibility (never leaks RTSP credentials)
    visible_cams = [serialize_camera(c) for c in cams]

    return DashboardOverviewResponse(
        target_date=dt.isoformat(),
        total_employees=total_employees,
        currently_present=currently_present,
        absent_today=absent_today,
        on_leave_today=on_leave_today,
        late_arrivals=late_arrivals,
        early_departures=early_departures,
        office_occupancy_count=office_occupancy_count,
        office_capacity=office_capacity,
        office_occupancy_percent=office_occupancy_percent,
        cameras_online=cameras_online,
        cameras_total=cameras_total,
        pending_leaves=pending_leaves,
        pending_corrections=pending_corrections,
        unreviewed_alerts=unreviewed_alerts,
        department_attendance=dept_metrics,
        attendance_trends=trends,
        recent_events=[serialize_vision_event(e) for e in recent_events],
        cameras=visible_cams,
        ethics_disclosure={
            "presence_is_not_productivity": True,
            "facial_recognition_enabled": False,
            "emotion_recognition_enabled": False,
            "automated_scoring_enabled": False,
            "ai_detector_backend": person_detector.backend_name,
            "note": (
                "Verified Attendance (access card / QR / portal) is strictly separated from "
                "anonymous AI physical occupancy telemetry. Physical presence never establishes productivity."
            ),
        },
    )


@router.get("/employee-self")
def get_employee_self_dashboard(
    current_user: User = Depends(require_roles(ALL_ROLES)),
    db: Session = Depends(get_db),
):
    """Self-service dashboard exclusively scoped to the signed-in employee."""
    if not current_user.employee_id:
        raise HTTPException(status_code=404, detail="No employee profile associated with this account.")

    emp = db.query(Employee).filter(Employee.id == current_user.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found.")

    today = date.today()
    month_start = today - timedelta(days=29)

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.attendance_date >= month_start,
        )
        .order_by(AttendanceRecord.attendance_date.desc())
        .all()
    )
    today_record = next((r for r in records if r.attendance_date == today), None)
    leaves = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == emp.id)
        .order_by(LeaveRequest.created_at.desc())
        .all()
    )
    corrections = (
        db.query(AttendanceCorrection)
        .filter(AttendanceCorrection.employee_id == emp.id)
        .order_by(AttendanceCorrection.created_at.desc())
        .all()
    )
    policy = db.query(RetentionPolicy).first()

    total_hours_30d = round(sum(r.working_hours for r in records), 2)
    days_present_30d = sum(
        1 for r in records if r.status in ("present", "late", "early_departure", "late_and_early")
    )
    late_days_30d = sum(1 for r in records if r.status in ("late", "late_and_early"))

    return {
        "employee": {
            "id": emp.id,
            "employee_code": emp.employee_code,
            "full_name": emp.full_name,
            "email": emp.email,
            "job_title": emp.job_title,
            "department_name": emp.department.name if emp.department else "Unassigned",
            "shift_name": emp.shift.name if emp.shift else "Core Day Shift",
            "shift_hours": f"{emp.shift.start_time} – {emp.shift.end_time}" if emp.shift else "09:00 – 17:30",
            "badge_id": emp.badge_id,
            "workspace_desk_label": emp.workspace_desk_label,
            "privacy_consent_accepted": emp.privacy_consent_accepted,
            "privacy_consent_at": emp.privacy_consent_at,
        },
        "today_record": (
            {
                "id": today_record.id,
                "status": today_record.status,
                "check_in_time": today_record.check_in_time,
                "check_out_time": today_record.check_out_time,
                "working_hours": today_record.working_hours,
                "verification_method": today_record.verification_method,
            }
            if today_record
            else None
        ),
        "metrics_30d": {
            "total_working_hours": total_hours_30d,
            "days_present": days_present_30d,
            "late_arrivals": late_days_30d,
            "avg_daily_hours": round(total_hours_30d / max(1, days_present_30d), 2),
            "pending_leaves": sum(1 for l in leaves if l.status == "pending"),
            "pending_corrections": sum(1 for c in corrections if c.status == "pending"),
        },
        "recent_attendance": [
            {
                "id": r.id,
                "attendance_date": r.attendance_date.isoformat(),
                "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
                "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
                "status": r.status,
                "working_hours": r.working_hours,
                "verification_method": r.verification_method,
                "is_corrected": r.is_corrected,
            }
            for r in records[:14]
        ],
        "monitoring_policy": {
            "version": policy.monitoring_notice_version if policy else "2026.1",
            "notice_text": policy.monitoring_notice_text if policy else "",
            "video_retention_days": policy.video_retention_days if policy else 7,
            "raw_video_storage_enabled": policy.enable_raw_video_storage if policy else False,
        },
    }
