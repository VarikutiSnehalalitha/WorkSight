export type UserRole = "super_admin" | "hr_admin" | "dept_manager" | "employee";

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  can_view_cctv: boolean;
  managed_department_id: number | null;
  managed_department_name: string | null;
  employee_id: number | null;
  employee_code: string | null;
  department_id: number | null;
  department_name: string | null;
  privacy_consent_accepted: boolean | null;
  privacy_consent_at: string | null;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  floor_location: string;
  description: string | null;
  target_capacity: number;
  employee_count: number;
  present_today: number;
  late_today: number;
  on_leave_today: number;
  absent_today: number;
  ai_observed_occupancy: number;
  attendance_rate: number;
}

export interface Shift {
  id: number;
  name: string;
  start_time: string;
  end_time: string;
  grace_period_minutes: number;
  early_departure_threshold_minutes: number;
  is_default: boolean;
}

export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  email: string;
  phone: string | null;
  job_title: string;
  department_id: number;
  department_name: string | null;
  shift_id: number | null;
  shift_name: string | null;
  badge_id: string;
  employment_status: string;
  hire_date: string;
  workspace_desk_label: string | null;
  privacy_consent_accepted: boolean;
  today_status: string | null;
  today_check_in: string | null;
}

export interface AttendanceRecord {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department_id: number;
  department_name: string;
  attendance_date: string;
  check_in_time: string | null;
  check_out_time: string | null;
  verification_method: string;
  record_category: string;
  status: string;
  working_hours: number;
  late_minutes: number;
  early_departure_minutes: number;
  notes: string | null;
  is_corrected: boolean;
}

export interface AttendanceCorrection {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department_name: string;
  attendance_record_id: number | null;
  attendance_date: string;
  requested_check_in: string | null;
  requested_check_out: string | null;
  reason: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by_name: string | null;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department_id: number;
  department_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days_count: number;
  reason: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by_name: string | null;
  review_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface MonitoringZone {
  id: number;
  camera_id: number;
  name: string;
  zone_type: "workspace" | "entry_exit" | "restricted" | "common_area";
  coordinates: number[][];
  max_occupancy: number;
  vacancy_alert_minutes: number;
  is_active: boolean;
  current_count: number;
  last_occupied_at: string | null;
}

export interface Camera {
  id: number;
  name: string;
  location: string;
  department_id: number | null;
  department_name: string | null;
  camera_type: "rtsp" | "onvif" | "simulated";
  is_simulated: boolean;
  masked_endpoint: string;
  status: "online" | "offline" | "degraded" | "reconnecting" | "obstructed";
  resolution: string;
  fps: number;
  last_heartbeat_at: string | null;
  reconnect_attempts: number;
  current_occupancy: number;
  max_occupancy_threshold: number;
  ai_enabled: boolean;
  recording_enabled: boolean;
  zones: MonitoringZone[];
}

export interface OnvifDevice {
  name: string;
  ip_address: string;
  port: number;
  manufacturer: string;
  model: string;
  onvif_service_url: string;
  is_simulated_discovery: boolean;
}

export interface VisionEvent {
  id: number;
  camera_id: number;
  camera_name: string;
  camera_location: string;
  zone_id: number | null;
  zone_name: string | null;
  event_type: string;
  source_category: string;
  severity: "info" | "warning" | "critical";
  person_count: number;
  anonymous_track_ids: string[];
  confidence: number;
  description: string;
  is_simulated: boolean;
  review_status: "unreviewed" | "confirmed" | "false_positive" | "resolved";
  reviewed_by_name: string | null;
  review_notes: string | null;
  reviewed_at: string | null;
  occurred_at: string;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  category: string;
  severity: "info" | "warning" | "critical";
  is_read: boolean;
  review_status: "pending" | "acknowledged" | "resolved" | "dismissed";
  review_notes: string | null;
  related_event_id: number | null;
  created_at: string;
}

export interface RetentionPolicy {
  id: number;
  video_retention_days: number;
  event_metadata_retention_days: number;
  enable_raw_video_storage: boolean;
  auto_purge_enabled: boolean;
  last_purge_at: string | null;
  last_purge_deleted_count: number;
  monitoring_notice_version: string;
  monitoring_notice_text: string;
  updated_at: string | null;
}

export interface AuditLog {
  id: number;
  user_email: string;
  user_role: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface AttendanceTrendPoint {
  date: string;
  present: number;
  late: number;
  absent: number;
  on_leave: number;
  ai_peak_occupancy: number;
}

export interface DashboardOverview {
  target_date: string;
  total_employees: number;
  currently_present: number;
  absent_today: number;
  on_leave_today: number;
  late_arrivals: number;
  early_departures: number;
  office_occupancy_count: number;
  office_capacity: number;
  office_occupancy_percent: number;
  cameras_online: number;
  cameras_total: number;
  pending_leaves: number;
  pending_corrections: number;
  unreviewed_alerts: number;
  department_attendance: Department[];
  attendance_trends: AttendanceTrendPoint[];
  recent_events: VisionEvent[];
  cameras: Camera[];
  ethics_disclosure: {
    presence_is_not_productivity: boolean;
    facial_recognition_enabled: boolean;
    emotion_recognition_enabled: boolean;
    automated_scoring_enabled: boolean;
    ai_detector_backend: string;
    note: string;
  };
}

export interface EmployeeSelfSummary {
  employee: {
    id: number;
    employee_code: string;
    full_name: string;
    email: string;
    job_title: string;
    department_name: string;
    shift_name: string;
    shift_hours: string;
    badge_id: string;
    workspace_desk_label: string | null;
    privacy_consent_accepted: boolean;
    privacy_consent_at: string | null;
  };
  today_record: {
    id: number;
    status: string;
    check_in_time: string | null;
    check_out_time: string | null;
    working_hours: number;
    verification_method: string;
  } | null;
  metrics_30d: {
    total_working_hours: number;
    days_present: number;
    late_arrivals: number;
    avg_daily_hours: number;
    pending_leaves: number;
    pending_corrections: number;
  };
  recent_attendance: Array<{
    id: number;
    attendance_date: string;
    check_in_time: string | null;
    check_out_time: string | null;
    status: string;
    working_hours: number;
    verification_method: string;
    is_corrected: boolean;
  }>;
  monitoring_policy: {
    version: string;
    notice_text: string;
    video_retention_days: number;
    raw_video_storage_enabled: boolean;
  };
}
