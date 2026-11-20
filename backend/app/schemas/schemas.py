from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==============================================================================
# Auth & User Schemas
# ==============================================================================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    can_view_cctv: bool
    managed_department_id: Optional[int] = None
    managed_department_name: Optional[str] = None
    employee_id: Optional[int] = None
    employee_code: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    privacy_consent_accepted: Optional[bool] = None
    privacy_consent_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class ConsentUpdateRequest(BaseModel):
    accepted: bool


# ==============================================================================
# Department & Shift Schemas
# ==============================================================================
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=24)
    floor_location: str = Field(default="Floor 1", max_length=120)
    description: Optional[str] = None
    target_capacity: int = Field(default=20, ge=1, le=500)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    floor_location: Optional[str] = None
    description: Optional[str] = None
    target_capacity: Optional[int] = Field(default=None, ge=1, le=500)


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    floor_location: str
    description: Optional[str] = None
    target_capacity: int
    employee_count: int = 0
    present_today: int = 0
    late_today: int = 0
    on_leave_today: int = 0
    absent_today: int = 0
    ai_observed_occupancy: int = 0
    attendance_rate: float = 0.0


class ShiftCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    grace_period_minutes: int = Field(default=15, ge=0, le=120)
    early_departure_threshold_minutes: int = Field(default=15, ge=0, le=120)
    is_default: bool = False


class ShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_time: str
    end_time: str
    grace_period_minutes: int
    early_departure_threshold_minutes: int
    is_default: bool


# ==============================================================================
# Employee Schemas
# ==============================================================================
class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=2, max_length=32)
    full_name: str = Field(min_length=2, max_length=140)
    email: EmailStr
    phone: Optional[str] = None
    job_title: str = Field(default="Associate", max_length=120)
    department_id: int
    shift_id: Optional[int] = None
    badge_id: Optional[str] = None
    workspace_desk_label: Optional[str] = None
    hire_date: Optional[date] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[int] = None
    shift_id: Optional[int] = None
    employment_status: Optional[str] = None
    workspace_desk_label: Optional[str] = None


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    email: str
    phone: Optional[str] = None
    job_title: str
    department_id: int
    department_name: Optional[str] = None
    shift_id: Optional[int] = None
    shift_name: Optional[str] = None
    badge_id: str
    employment_status: str
    hire_date: date
    workspace_desk_label: Optional[str] = None
    privacy_consent_accepted: bool
    today_status: Optional[str] = None
    today_check_in: Optional[datetime] = None


# ==============================================================================
# Attendance & Correction Schemas
# ==============================================================================
class CheckInOutRequest(BaseModel):
    employee_id: Optional[int] = None  # Ignored for employee role (always self)
    verification_method: str = Field(default="qr_code")
    # access_card | qr_code | web_portal
    notes: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_id: int
    department_name: str
    attendance_date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    verification_method: str
    record_category: str
    status: str
    working_hours: float
    late_minutes: int
    early_departure_minutes: int
    notes: Optional[str] = None
    is_corrected: bool


class CorrectionCreateRequest(BaseModel):
    attendance_record_id: Optional[int] = None
    attendance_date: date
    requested_check_in: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    requested_check_out: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    reason: str = Field(min_length=5, max_length=600)


class CorrectionReviewRequest(BaseModel):
    status: str = Field(pattern=r"^(approved|rejected)$")
    review_notes: Optional[str] = None


class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_name: str
    attendance_record_id: Optional[int] = None
    attendance_date: date
    requested_check_in: Optional[str] = None
    requested_check_out: Optional[str] = None
    reason: str
    status: str
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


# ==============================================================================
# Leave Schemas
# ==============================================================================
class LeaveCreateRequest(BaseModel):
    leave_type: str = Field(pattern=r"^(annual|sick|personal|parental|unpaid)$")
    start_date: date
    end_date: date
    reason: str = Field(min_length=5, max_length=600)


class LeaveReviewRequest(BaseModel):
    status: str = Field(pattern=r"^(approved|rejected)$")
    review_notes: Optional[str] = None


class LeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    department_id: int
    department_name: str
    leave_type: str
    start_date: date
    end_date: date
    days_count: int
    reason: str
    status: str
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


# ==============================================================================
# CCTV & Monitoring Zone Schemas (Zero Credential Leakage)
# ==============================================================================
class MonitoringZoneCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    zone_type: str = Field(pattern=r"^(workspace|entry_exit|restricted|common_area)$")
    coordinates: List[List[float]] = Field(
        default=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
    )
    max_occupancy: int = Field(default=10, ge=0, le=500)
    vacancy_alert_minutes: int = Field(default=45, ge=5, le=720)
    is_active: bool = True


class MonitoringZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    name: str
    zone_type: str
    coordinates: List[List[float]]
    max_occupancy: int
    vacancy_alert_minutes: int
    is_active: bool
    current_count: int
    last_occupied_at: Optional[datetime] = None


class CameraCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=160)
    department_id: Optional[int] = None
    camera_type: str = Field(default="rtsp", pattern=r"^(rtsp|onvif|simulated)$")
    is_simulated: bool = False
    rtsp_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    max_occupancy_threshold: int = Field(default=12, ge=1, le=500)
    ai_enabled: bool = True
    recording_enabled: bool = False


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    department_id: Optional[int] = None
    rtsp_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    max_occupancy_threshold: Optional[int] = Field(default=None, ge=1, le=500)
    ai_enabled: Optional[bool] = None
    recording_enabled: Optional[bool] = None
    status: Optional[str] = None


class CameraResponse(BaseModel):
    """Strictly omits raw RTSP URLs, usernames, and passwords."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    camera_type: str
    is_simulated: bool
    masked_endpoint: str
    status: str
    resolution: str
    fps: float
    last_heartbeat_at: Optional[datetime] = None
    reconnect_attempts: int
    current_occupancy: int
    max_occupancy_threshold: int
    ai_enabled: bool
    recording_enabled: bool
    zones: List[MonitoringZoneResponse] = []


class CameraConnectionTestRequest(BaseModel):
    rtsp_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_simulated: bool = False


class CameraConnectionTestResponse(BaseModel):
    reachable: bool
    is_simulated: bool
    masked_endpoint: str
    resolution: Optional[str] = None
    fps: Optional[float] = None
    latency_ms: float
    message: str


class OnvifDeviceDiscovered(BaseModel):
    name: str
    ip_address: str
    port: int
    manufacturer: str
    model: str
    onvif_service_url: str
    is_simulated_discovery: bool = False


# ==============================================================================
# AI Vision Events & Notifications
# ==============================================================================
class VisionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    camera_name: str
    camera_location: str
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    event_type: str
    source_category: str
    severity: str
    person_count: int
    anonymous_track_ids: List[str]
    confidence: float
    description: str
    is_simulated: bool
    review_status: str
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    occurred_at: datetime


class VisionEventReviewRequest(BaseModel):
    review_status: str = Field(pattern=r"^(confirmed|false_positive|resolved)$")
    review_notes: Optional[str] = None


class SimulateVisionEventRequest(BaseModel):
    camera_id: int
    event_type: str = Field(
        pattern=r"^(entry|exit|occupancy_change|restricted_intrusion|extended_vacancy|crowd_detected|camera_obstructed|camera_disconnected)$"
    )
    person_count: int = Field(default=1, ge=0, le=100)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    category: str
    severity: str
    is_read: bool
    review_status: str
    review_notes: Optional[str] = None
    related_event_id: Optional[int] = None
    created_at: datetime


class NotificationReviewRequest(BaseModel):
    is_read: Optional[bool] = None
    review_status: Optional[str] = Field(
        default=None, pattern=r"^(pending|acknowledged|resolved|dismissed)$"
    )
    review_notes: Optional[str] = None


# ==============================================================================
# Privacy, Retention & Audit Logs
# ==============================================================================
class RetentionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_retention_days: int
    event_metadata_retention_days: int
    enable_raw_video_storage: bool
    auto_purge_enabled: bool
    last_purge_at: Optional[datetime] = None
    last_purge_deleted_count: int
    monitoring_notice_version: str
    monitoring_notice_text: str
    updated_at: Optional[datetime] = None


class RetentionPolicyUpdate(BaseModel):
    video_retention_days: Optional[int] = Field(default=None, ge=1, le=90)
    event_metadata_retention_days: Optional[int] = Field(default=None, ge=7, le=365)
    enable_raw_video_storage: Optional[bool] = None
    auto_purge_enabled: Optional[bool] = None
    monitoring_notice_text: Optional[str] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_email: str
    user_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


# ==============================================================================
# Dashboard Overview Schemas
# ==============================================================================
class AttendanceTrendPoint(BaseModel):
    date: str
    present: int
    late: int
    absent: int
    on_leave: int
    ai_peak_occupancy: int


class DashboardOverviewResponse(BaseModel):
    target_date: str
    total_employees: int
    currently_present: int
    absent_today: int
    on_leave_today: int
    late_arrivals: int
    early_departures: int
    office_occupancy_count: int
    office_capacity: int
    office_occupancy_percent: float
    cameras_online: int
    cameras_total: int
    pending_leaves: int
    pending_corrections: int
    unreviewed_alerts: int
    department_attendance: List[DepartmentResponse]
    attendance_trends: List[AttendanceTrendPoint]
    recent_events: List[VisionEventResponse]
    cameras: List[CameraResponse]
    ethics_disclosure: Dict[str, Any]
