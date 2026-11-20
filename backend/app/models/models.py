from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    floor_location: Mapped[str] = mapped_column(String(120), default="Floor 1")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_capacity: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="department")
    cameras: Mapped[List["Camera"]] = relationship("Camera", back_populates="department")


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="17:30")
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=15)
    early_departure_threshold_minutes: Mapped[int] = mapped_column(Integer, default=15)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="shift")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(140), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    job_title: Mapped[str] = mapped_column(String(120), default="Associate")
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False, index=True)
    shift_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shifts.id"), nullable=True)
    badge_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    employment_status: Mapped[str] = mapped_column(String(32), default="active")
    hire_date: Mapped[date] = mapped_column(Date, default=date.today)
    workspace_desk_label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    privacy_consent_accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    privacy_consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    department: Mapped["Department"] = relationship("Department", back_populates="employees")
    shift: Mapped[Optional["Shift"]] = relationship("Shift", back_populates="employees")
    user_account: Mapped[Optional["User"]] = relationship("User", back_populates="employee", uselist=False)
    attendance_records: Mapped[List["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="employee", cascade="all, delete-orphan"
    )
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="employee", cascade="all, delete-orphan"
    )
    correction_requests: Mapped[List["AttendanceCorrection"]] = relationship(
        "AttendanceCorrection", back_populates="employee", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(140), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # Allowed roles: super_admin, hr_admin, dept_manager, employee
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_cctv: Mapped[bool] = mapped_column(Boolean, default=False)
    managed_department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="user_account")
    managed_department: Mapped[Optional["Department"]] = relationship(
        "Department", foreign_keys=[managed_department_id]
    )


class AttendanceRecord(Base):
    """Verified individual attendance records (access card, QR check-in, web portal, or HR verified).

    Explicitly separated from AI Vision presence telemetry; CCTV never writes individual attendance.
    """

    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_method: Mapped[str] = mapped_column(String(32), default="access_card")
    # access_card | qr_code | web_portal | hr_adjusted
    record_category: Mapped[str] = mapped_column(String(32), default="verified_attendance")
    status: Mapped[str] = mapped_column(String(32), default="present")
    # present | late | early_departure | late_and_early | absent | on_leave
    working_hours: Mapped[float] = mapped_column(Float, default=0.0)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_departure_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    attendance_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("attendance_records.id"), nullable=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_check_in: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    requested_check_out: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    # pending | approved | rejected
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="correction_requests")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    leave_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # annual | sick | personal | parental | unpaid
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_count: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    # pending | approved | rejected
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="leave_requests")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    camera_type: Mapped[str] = mapped_column(String(24), default="simulated")
    # rtsp | onvif | simulated
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    # Encrypted secrets — NEVER serialized to frontend API responses
    rtsp_url_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    username_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    masked_endpoint: Mapped[str] = mapped_column(String(255), default="simulated://local-dev-feed")
    status: Mapped[str] = mapped_column(String(24), default="online", index=True)
    # online | offline | degraded | reconnecting | obstructed
    resolution: Mapped[str] = mapped_column(String(32), default="1280x720")
    fps: Mapped[float] = mapped_column(Float, default=15.0)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utcnow)
    reconnect_attempts: Mapped[int] = mapped_column(Integer, default=0)
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    max_occupancy_threshold: Mapped[int] = mapped_column(Integer, default=12)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    recording_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="cameras")
    zones: Mapped[List["MonitoringZone"]] = relationship(
        "MonitoringZone", back_populates="camera", cascade="all, delete-orphan"
    )
    events: Mapped[List["VisionEvent"]] = relationship(
        "VisionEvent", back_populates="camera", cascade="all, delete-orphan"
    )


class MonitoringZone(Base):
    __tablename__ = "monitoring_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(32), default="workspace")
    # workspace | entry_exit | restricted | common_area
    coordinates_json: Mapped[str] = mapped_column(
        Text, default="[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]"
    )
    max_occupancy: Mapped[int] = mapped_column(Integer, default=10)
    vacancy_alert_minutes: Mapped[int] = mapped_column(Integer, default=45)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    last_occupied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utcnow)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="zones")


class VisionEvent(Base):
    """Anonymous AI Computer Vision telemetry events.

    Tracks physical presence, zone counts, entry/exit crossings, restricted area alerts,
    vacancy, crowding, and camera health. Never identifies individuals by face or appearance.
    """

    __tablename__ = "vision_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False, index=True)
    zone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("monitoring_zones.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    # entry | exit | occupancy_change | restricted_intrusion | extended_vacancy
    # crowd_detected | camera_obstructed | camera_disconnected
    source_category: Mapped[str] = mapped_column(String(32), default="ai_presence_telemetry")
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)
    # info | warning | critical
    person_count: Mapped[int] = mapped_column(Integer, default=0)
    anonymous_track_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    review_status: Mapped[str] = mapped_column(String(24), default="unreviewed", index=True)
    # unreviewed | confirmed | false_positive | resolved
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="events")
    zone: Mapped[Optional["MonitoringZone"]] = relationship("MonitoringZone")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="system", index=True)
    # camera | occupancy | restricted_area | vacancy | attendance | leave | system
    severity: Mapped[str] = mapped_column(String(16), default="info")
    # info | warning | critical
    target_roles: Mapped[str] = mapped_column(String(120), default="super_admin,hr_admin")
    target_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    related_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vision_events.id"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="pending")
    # pending | acknowledged | resolved | dismissed
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_retention_days: Mapped[int] = mapped_column(Integer, default=7)
    event_metadata_retention_days: Mapped[int] = mapped_column(Integer, default=90)
    enable_raw_video_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_purge_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_purge_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_purge_deleted_count: Mapped[int] = mapped_column(Integer, default=0)
    monitoring_notice_version: Mapped[str] = mapped_column(String(24), default="2026.1")
    monitoring_notice_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    user_email: Mapped[str] = mapped_column(String(160), default="system")
    user_role: Mapped[str] = mapped_column(String(32), default="system")
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
