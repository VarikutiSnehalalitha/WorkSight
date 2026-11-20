"""Department Management & Department-Wise Attendance/Occupancy Endpoints."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_AND_HR,
    MANAGEMENT_ROLES,
    ROLE_DEPT_MANAGER,
    require_roles,
)
from app.core.database import get_db
from app.models.models import AttendanceRecord, Camera, Department, Employee, User
from app.schemas.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/api/departments", tags=["Departments"])


def compute_department_metrics(
    db: Session, dept: Department, target_date: date
) -> DepartmentResponse:
    employees = db.query(Employee).filter(Employee.department_id == dept.id).all()
    emp_ids = [e.id for e in employees]
    emp_count = len(emp_ids)

    present = late = on_leave = absent = 0
    if emp_ids:
        records = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.employee_id.in_(emp_ids),
                AttendanceRecord.attendance_date == target_date,
            )
            .all()
        )
        rec_by_emp = {r.employee_id: r for r in records}
        for eid in emp_ids:
            r = rec_by_emp.get(eid)
            if not r or r.status == "absent":
                absent += 1
            elif r.status == "on_leave":
                on_leave += 1
            elif r.status in ("late", "late_and_early"):
                present += 1
                late += 1
            else:
                present += 1

    cameras = db.query(Camera).filter(Camera.department_id == dept.id).all()
    ai_occ = sum(c.current_occupancy for c in cameras if c.status == "online")
    active_denominator = max(1, emp_count - on_leave)
    rate = round((present / active_denominator) * 100.0, 1) if emp_count > 0 else 0.0

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        floor_location=dept.floor_location,
        description=dept.description,
        target_capacity=dept.target_capacity,
        employee_count=emp_count,
        present_today=present,
        late_today=late,
        on_leave_today=on_leave,
        absent_today=absent,
        ai_observed_occupancy=ai_occ,
        attendance_rate=rate,
    )


@router.get("", response_model=List[DepartmentResponse])
def list_departments(
    target_date: Optional[date] = Query(default=None),
    current_user: User = Depends(require_roles(MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    dt = target_date or date.today()
    q = db.query(Department)
    if current_user.role == ROLE_DEPT_MANAGER:
        q = q.filter(Department.id == current_user.managed_department_id)
    depts = q.order_by(Department.name.asc()).all()
    return [compute_department_metrics(db, d, dt) for d in depts]


@router.post("", response_model=DepartmentResponse, status_code=201)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    exists = (
        db.query(Department)
        .filter((Department.name == payload.name) | (Department.code == payload.code.upper()))
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Department name or code already exists.")

    dept = Department(
        name=payload.name,
        code=payload.code.upper(),
        floor_location=payload.floor_location,
        description=payload.description,
        target_capacity=payload.target_capacity,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    log_audit(
        db=db,
        action="department_created",
        resource_type="department",
        resource_id=str(dept.id),
        details=f"Created department {dept.name} ({dept.code}).",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return compute_department_metrics(db, dept, date.today())


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    request: Request,
    current_user: User = Depends(require_roles(ADMIN_AND_HR)),
    db: Session = Depends(get_db),
):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    if payload.name is not None:
        dept.name = payload.name
    if payload.floor_location is not None:
        dept.floor_location = payload.floor_location
    if payload.description is not None:
        dept.description = payload.description
    if payload.target_capacity is not None:
        dept.target_capacity = payload.target_capacity

    db.commit()
    db.refresh(dept)

    log_audit(
        db=db,
        action="department_updated",
        resource_type="department",
        resource_id=str(dept.id),
        details=f"Updated department {dept.name}.",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return compute_department_metrics(db, dept, date.today())
