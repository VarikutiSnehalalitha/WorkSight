"""Initial WorkSight enterprise schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("code", sa.String(24), nullable=False, unique=True),
        sa.Column("floor_location", sa.String(120), nullable=False, server_default="Floor 1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_capacity", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("start_time", sa.String(5), nullable=False, server_default="09:00"),
        sa.Column("end_time", sa.String(5), nullable=False, server_default="17:30"),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("early_departure_threshold_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_code", sa.String(32), nullable=False, unique=True),
        sa.Column("full_name", sa.String(140), nullable=False),
        sa.Column("email", sa.String(160), nullable=False, unique=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("job_title", sa.String(120), nullable=False, server_default="Associate"),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("shift_id", sa.Integer(), sa.ForeignKey("shifts.id"), nullable=True),
        sa.Column("badge_id", sa.String(64), nullable=False, unique=True),
        sa.Column("employment_status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("workspace_desk_label", sa.String(64), nullable=True),
        sa.Column("privacy_consent_accepted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("privacy_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_employees_department_id", "employees", ["department_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(160), nullable=False, unique=True),
        sa.Column("full_name", sa.String(140), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_view_cctv", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("managed_department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_method", sa.String(32), nullable=False, server_default="access_card"),
        sa.Column("record_category", sa.String(32), nullable=False, server_default="verified_attendance"),
        sa.Column("status", sa.String(32), nullable=False, server_default="present"),
        sa.Column("working_hours", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("late_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_departure_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_corrected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_attendance_employee_date", "attendance_records", ["employee_id", "attendance_date"])

    op.create_table(
        "attendance_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("attendance_record_id", sa.Integer(), sa.ForeignKey("attendance_records.id"), nullable=True),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("requested_check_in", sa.String(10), nullable=True),
        sa.Column("requested_check_out", sa.String(10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("leave_type", sa.String(32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("camera_type", sa.String(24), nullable=False, server_default="simulated"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rtsp_url_encrypted", sa.Text(), nullable=True),
        sa.Column("username_encrypted", sa.Text(), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("masked_endpoint", sa.String(255), nullable=False, server_default="simulated://local-dev-feed"),
        sa.Column("status", sa.String(24), nullable=False, server_default="online"),
        sa.Column("resolution", sa.String(32), nullable=False, server_default="1280x720"),
        sa.Column("fps", sa.Float(), nullable=False, server_default="15.0"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconnect_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_occupancy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_occupancy_threshold", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("recording_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "monitoring_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("zone_type", sa.String(32), nullable=False, server_default="workspace"),
        sa.Column("coordinates_json", sa.Text(), nullable=False),
        sa.Column("max_occupancy", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("vacancy_alert_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_occupied_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "vision_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("monitoring_zones.id"), nullable=True),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("source_category", sa.String(32), nullable=False, server_default="ai_presence_telemetry"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("person_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anonymous_track_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("review_status", sa.String(24), nullable=False, server_default="unreviewed"),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False, server_default="system"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("target_roles", sa.String(120), nullable=False, server_default="super_admin,hr_admin"),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("related_event_id", sa.Integer(), sa.ForeignKey("vision_events.id"), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_retention_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("event_metadata_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("enable_raw_video_storage", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_purge_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_purge_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_purge_deleted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monitoring_notice_version", sa.String(24), nullable=False, server_default="2026.1"),
        sa.Column("monitoring_notice_text", sa.Text(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_email", sa.String(160), nullable=False, server_default="system"),
        sa.Column("user_role", sa.String(32), nullable=False, server_default="system"),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("retention_policies")
    op.drop_table("notifications")
    op.drop_table("vision_events")
    op.drop_table("monitoring_zones")
    op.drop_table("cameras")
    op.drop_table("leave_requests")
    op.drop_table("attendance_corrections")
    op.drop_table("attendance_records")
    op.drop_table("users")
    op.drop_table("employees")
    op.drop_table("shifts")
    op.drop_table("departments")
