"""Employee Directory & Management Endpoints (Strictly Role & Department Scoped)."""

from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_AND_HR,
    MANAGEMENT_ROLES,
    require_roles,
    resolve_department_scope,
)
from app.core.database import get_db
from app.models.models import AttendanceRecord, Department, Employee, Shift, User
from app.schemas.schemas import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/api/employees", tags=["Employees"])


def serialize_employee(db: Session, emp: Employee, today_rec: Optional[AttendanceRecord] = None) -> EmployeeResponse:
    return EmployeeResponse(
        id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        email=emp.email,
        phone=emp.phone,
        job_title=emp.job_title,
        department_id=emp.department_id,
        department_name=emp.department.name if emp.department else None,
        shift_id=emp.shift_id,
        shift_name=emp.shift.name if emp.shift else None,
        badge_id=emp.badge_id,
        employment_status=emp.employment_status,
        hire_date=emp.hire_date,
        workspace_desk_label=emp.workspace_desk_label,
        privacy_consent_accepted=emp.privacy_consent_accepted,
        today_status=today_rec.status if today_rec else "unrecorded",
        today_check_in=today_rec.check_in_time if today_rec else None,
    )


@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    department_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    scoped_dept = resolve_department_scope(current_user, department_id)
    q = db.query(Employee)
    if scoped_dept is not None:
        q = q.filter(Employee.department_id == scoped_dept)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            Employee.full_name.ilike(term)
            | Employee.email.ilike(term)
            | Employee.employee_code.ilike(term)
            | Employee.job_title.ilike(term)
        )
    if status_filter:
        q = q.filter(Employee.employment_status == status_filter)

    employees = q.order_by(Employee.employee_code.asc()).all()
    today = date.today()
    today_recs = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.attendance_date == today)
        .all()
    )
    rec_map = {r.employee_id: r for r in today_recs}
    return [serialize_employee(db, e, rec_map.get(e.id)) for e in employees]


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    dept = db.query(Department).filter(Department.id == payload.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    dup = (
        db.query(Employee)
        .filter(
            (Employee.email == payload.email.lower())
            | (Employee.employee_code == payload.employee_code.upper())
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Employee with this email or code already exists.")

    shift_id = payload.shift_id
    if shift_id is None:
        default_shift = db.query(Shift).filter(Shift.is_default == True).first()  # noqa: E712
        shift_id = default_shift.id if default_shift else None

    badge_id = payload.badge_id or f"CARD-{payload.employee_code.upper()}"
    emp = Employee(
        employee_code=payload.employee_code.upper(),
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        job_title=payload.job_title,
        department_id=payload.department_id,
        shift_id=shift_id,
        badge_id=badge_id,
        workspace_desk_label=payload.workspace_desk_label,
        hire_date=payload.hire_date or date.today(),
        privacy_consent_accepted=True,
        privacy_consent_at=datetime.now(timezone.utc),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    log_audit(
        db=db,
        action="employee_created",
        resource_type="employee",
        resource_id=str(emp.id),
        details=f"Added employee {emp.full_name} ({emp.employee_code}) to {dept.name}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return serialize_employee(db, emp)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    if payload.full_name is not None:
        emp.full_name = payload.full_name
    if payload.phone is not None:
        emp.phone = payload.phone
    if payload.job_title is not None:
        emp.job_title = payload.job_title
    if payload.department_id is not None:
        emp.department_id = payload.department_id
    if payload.shift_id is not None:
        emp.shift_id = payload.shift_id
    if payload.employment_status is not None:
        emp.employment_status = payload.employment_status
    if payload.workspace_desk_label is not None:
        emp.workspace_desk_label = payload.workspace_desk_label

    db.commit()
    db.refresh(emp)

    log_audit(
        db=db,
        action="employee_updated",
        resource_type="employee",
        resource_id=str(emp.id),
        details=f"Updated employee profile {emp.employee_code}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    today_rec = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.attendance_date == date.today(),
        )
        .first()
    )
    return serialize_employee(db, emp, today_rec)


@router.delete("/{employee_id}")
def deactivate_employee(
    employee_id: int,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
    emp.employment_status = "inactive"
    db.commit()
    log_audit(
        db=db,
        action="employee_deactivated",
        resource_type="employee",
        resource_id=str(emp.id),
        details=f"Deactivated employee {emp.employee_code}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "deactivated", "employee_id": employee_id}
