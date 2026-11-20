"""Department & Attendance Analytics Reports + Excel/PDF Exports."""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import (
    MANAGEMENT_ROLES,
    require_roles,
    resolve_department_scope,
)
from app.core.database import get_db
from app.models.models import AttendanceRecord, Department, Employee, User
from app.services.audit import log_audit
from app.services.reports import generate_attendance_excel, generate_attendance_pdf

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def _compile_report_data(
    db: Session,
    start_date: date,
    end_date: date,
    department_id: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    dept_q = db.query(Department)
    if department_id is not None:
        dept_q = dept_q.filter(Department.id == department_id)
    departments = dept_q.order_by(Department.name.asc()).all()

    rec_q = (
        db.query(AttendanceRecord)
        .join(Employee)
        .filter(
            AttendanceRecord.attendance_date >= start_date,
            AttendanceRecord.attendance_date <= end_date,
        )
    )
    if department_id is not None:
        rec_q = rec_q.filter(Employee.department_id == department_id)

    records = (
        rec_q.order_by(AttendanceRecord.attendance_date.desc(), Employee.full_name.asc()).all()
    )

    records_by_dept: Dict[int, List[AttendanceRecord]] = {}
    serialized_records: List[Dict[str, Any]] = []
    for r in records:
        emp = r.employee
        did = emp.department_id if emp else 0
        records_by_dept.setdefault(did, []).append(r)
        serialized_records.append(
            {
                "id": r.id,
                "attendance_date": r.attendance_date.isoformat(),
                "employee_code": emp.employee_code if emp else "-",
                "employee_name": emp.full_name if emp else "Unknown",
                "department_name": emp.department.name if (emp and emp.department) else "Unassigned",
                "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
                "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
                "status": r.status,
                "working_hours": r.working_hours,
                "late_minutes": r.late_minutes,
                "early_departure_minutes": r.early_departure_minutes,
                "verification_method": r.verification_method,
            }
        )

    summaries: List[Dict[str, Any]] = []
    for d in departments:
        emp_count = db.query(Employee).filter(Employee.department_id == d.id).count()
        drecs = records_by_dept.get(d.id, [])
        present = sum(1 for r in drecs if r.status in ("present", "late", "early_departure", "late_and_early"))
        late = sum(1 for r in drecs if r.status in ("late", "late_and_early"))
        early = sum(1 for r in drecs if r.status in ("early_departure", "late_and_early"))
        leave = sum(1 for r in drecs if r.status == "on_leave")
        absent = sum(1 for r in drecs if r.status == "absent")
        worked_hrs = [r.working_hours for r in drecs if r.working_hours > 0]
        avg_hrs = round(sum(worked_hrs) / len(worked_hrs), 2) if worked_hrs else 0.0
        denom = max(1, present + absent)
        rate = round((present / denom) * 100.0, 1) if (present + absent) > 0 else 0.0

        summaries.append(
            {
                "department_id": d.id,
                "department_name": d.name,
                "department_code": d.code,
                "employee_count": emp_count,
                "present_records": present,
                "late_records": late,
                "early_departures": early,
                "leave_records": leave,
                "absent_records": absent,
                "avg_working_hours": avg_hrs,
                "attendance_rate": rate,
            }
        )

    return summaries, serialized_records


@router.get("/summary")
def get_report_summary(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    e_date = end_date or date.today()
    s_date = start_date or (e_date - timedelta(days=13))
    scoped_dept = resolve_department_scope(current_user, department_id)

    summaries, records = _compile_report_data(db, s_date, e_date, scoped_dept)
    return {
        "start_date": s_date.isoformat(),
        "end_date": e_date.isoformat(),
        "department_summaries": summaries,
        "total_records": len(records),
        "records_preview": records[:100],
        "ethics_notice": (
            "Verified attendance metrics are strictly derived from access-card, QR, portal, "
            "or HR-approved records. Physical presence does not measure productivity."
        ),
    }


@router.get("/export/excel")
def export_excel_report(
    request: Request,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    e_date = end_date or date.today()
    s_date = start_date or (e_date - timedelta(days=13))
    scoped_dept = resolve_department_scope(current_user, department_id)

    summaries, records = _compile_report_data(db, s_date, e_date, scoped_dept)
    xlsx_bytes = generate_attendance_excel(s_date, e_date, summaries, records)

    log_audit(
        db=db,
        action="report_exported_excel",
        resource_type="report",
        details=f"Exported Excel attendance report ({s_date} to {e_date}, dept={scoped_dept}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )

    filename = f"worksight-attendance-{s_date.isoformat()}-to-{e_date.isoformat()}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/pdf")
def export_pdf_report(
    request: Request,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    e_date = end_date or date.today()
    s_date = start_date or (e_date - timedelta(days=13))
    scoped_dept = resolve_department_scope(current_user, department_id)

    summaries, records = _compile_report_data(db, s_date, e_date, scoped_dept)
    pdf_bytes = generate_attendance_pdf(s_date, e_date, summaries, records)

    log_audit(
        db=db,
        action="report_exported_pdf",
        resource_type="report",
        details=f"Exported PDF attendance report ({s_date} to {e_date}, dept={scoped_dept}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )

    filename = f"worksight-attendance-{s_date.isoformat()}-to-{e_date.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
