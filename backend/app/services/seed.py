"""Idempotent Enterprise Demo Data Seeder for WorkSight.

Creates realistic corporate departments, shifts, 24 employees, 4 RBAC demo portals,
14 days of verified attendance records, leave/correction workflows, clearly marked
SIMULATED development CCTV cameras with zones, AI vision telemetry events,
notifications, privacy/retention policy, and audit trail records.
"""

import json
import random
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.models import (
    AttendanceCorrection,
    AttendanceRecord,
    AuditLog,
    Camera,
    Department,
    Employee,
    LeaveRequest,
    MonitoringZone,
    Notification,
    RetentionPolicy,
    Shift,
    User,
    VisionEvent,
)

DEFAULT_MONITORING_NOTICE = (
    "WorkSight Transparent Workplace Monitoring & Privacy Policy (v2026.1)\n\n"
    "1. Purpose: WorkSight operates facility occupancy sensing and verified access-based attendance "
    "to support workplace safety, space planning, emergency headcount visibility, and transparent "
    "HR attendance administration.\n\n"
    "2. Strict Separation of Presence & Productivity: Physical presence in an office zone is NEVER "
    "used as a measure of individual employee productivity, performance, or engagement.\n\n"
    "3. Prohibited Technologies: WorkSight explicitly prohibits and does not implement facial "
    "recognition, biometric identification, emotion recognition, covert monitoring, automated "
    "employee scoring, or automated disciplinary decisions.\n\n"
    "4. Verified Attendance vs. Anonymous Vision Telemetry: Individual attendance records are "
    "captured solely through authorized access cards, QR check-in, or self-service portal actions. "
    "CCTV computer vision operates exclusively on anonymous person bounding boxes and aggregate "
    "zone counts.\n\n"
    "5. Retention, Access Control & Human Review: Raw video storage is disabled by default; event "
    "metadata automatically expires according to configured retention limits. Live feeds are "
    "restricted to explicitly authorized roles with immutable audit logging. Every alert requires "
    "human review before any action is taken.\n\n"
    "6. Employee Rights: Every employee may inspect their own attendance records, request "
    "corrections, review this policy at any time, and raise privacy questions with HR."
)


def seed_demo_data(db: Session) -> None:
    if db.query(User).count() > 0:
        return

    rng = random.Random(20261118)
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. Retention & Privacy Policy
    policy = RetentionPolicy(
        video_retention_days=7,
        event_metadata_retention_days=90,
        enable_raw_video_storage=False,
        auto_purge_enabled=True,
        last_purge_at=now - timedelta(hours=6),
        last_purge_deleted_count=14,
        monitoring_notice_version="2026.1",
        monitoring_notice_text=DEFAULT_MONITORING_NOTICE,
    )
    db.add(policy)

    # 2. Departments
    departments_data = [
        ("Engineering", "ENG", "Floor 3 — North Studio", "Core platform, backend, and AI infrastructure teams.", 16),
        ("Product & Design", "PRD", "Floor 3 — South Atelier", "Product management, UX research, and design systems.", 10),
        ("People & Operations", "OPS", "Floor 2 — Atrium Suite", "HR administration, workplace operations, and compliance.", 8),
        ("Finance & Legal", "FIN", "Floor 2 — West Wing", "Corporate finance, procurement, and legal governance.", 8),
        ("Client Advisory", "ADV", "Floor 1 — Client Pavilion", "Enterprise onboarding, solutions advisory, and account care.", 12),
    ]
    departments = []
    for name, code, floor, desc, cap in departments_data:
        d = Department(
            name=name,
            code=code,
            floor_location=floor,
            description=desc,
            target_capacity=cap,
        )
        db.add(d)
        departments.append(d)
    db.flush()

    dept_by_code = {d.code: d for d in departments}

    # 3. Shifts
    shifts_data = [
        ("Core Day Shift", "09:00", "17:30", 15, 15, True),
        ("Early Operations", "08:00", "16:30", 10, 15, False),
        ("Flexible Studio", "10:00", "18:30", 20, 15, False),
    ]
    shifts = []
    for name, st, et, grace, early, is_def in shifts_data:
        s = Shift(
            name=name,
            start_time=st,
            end_time=et,
            grace_period_minutes=grace,
            early_departure_threshold_minutes=early,
            is_default=is_def,
        )
        db.add(s)
        shifts.append(s)
    db.flush()

    core_shift, early_shift, flex_shift = shifts

    # 4. Employees (24 realistic staff across 5 departments)
    employees_seed = [
        # Engineering (7)
        ("WS-1001", "Eleanor Vance", "owner@worksight.io", "Chief Executive Officer", "OPS", core_shift, "Desk 2A-01"),
        ("WS-1002", "Nadia Al-Mansoor", "hr@worksight.io", "VP of People & Compliance", "OPS", core_shift, "Desk 2A-04"),
        ("WS-1003", "Marcus Sterling", "manager@worksight.io", "Director of Engineering", "ENG", core_shift, "Desk 3N-01"),
        ("WS-1004", "Maya Lin", "employee@worksight.io", "Senior Platform Engineer", "ENG", core_shift, "Desk 3N-04"),
        ("WS-1005", "Arjun Mehta", "arjun.mehta@worksight.io", "Computer Vision Engineer", "ENG", flex_shift, "Desk 3N-05"),
        ("WS-1006", "Claire Beaumont", "claire.beaumont@worksight.io", "Staff Systems Architect", "ENG", core_shift, "Desk 3N-06"),
        ("WS-1007", "Daniel Okafor", "daniel.okafor@worksight.io", "Backend Security Engineer", "ENG", core_shift, "Desk 3N-07"),
        ("WS-1008", "Sofia Lindholm", "sofia.lindholm@worksight.io", "Site Reliability Engineer", "ENG", early_shift, "Desk 3N-08"),
        ("WS-1009", "Kenji Takahashi", "kenji.takahashi@worksight.io", "Data Platform Engineer", "ENG", flex_shift, "Desk 3N-09"),
        # Product & Design (5)
        ("WS-1010", "Hannah Gallagher", "hannah.gallagher@worksight.io", "Head of Product Design", "PRD", core_shift, "Desk 3S-01"),
        ("WS-1011", "Mateo Silva", "mateo.silva@worksight.io", "Principal Product Manager", "PRD", core_shift, "Desk 3S-02"),
        ("WS-1012", "Priya Nair", "priya.nair@worksight.io", "Lead UX Researcher", "PRD", flex_shift, "Desk 3S-03"),
        ("WS-1013", "Liam Callahan", "liam.callahan@worksight.io", "Design Systems Designer", "PRD", core_shift, "Desk 3S-04"),
        ("WS-1014", "Amara Mensah", "amara.mensah@worksight.io", "Product Analyst", "PRD", core_shift, "Desk 3S-05"),
        # People & Operations (+2 more = 4 total)
        ("WS-1015", "Rachel Chen", "rachel.chen@worksight.io", "HR Operations Specialist", "OPS", early_shift, "Desk 2A-05"),
        ("WS-1016", "Tomasz Kowalski", "tomasz.kowalski@worksight.io", "Facilities & Safety Lead", "OPS", early_shift, "Desk 2A-06"),
        # Finance & Legal (4)
        ("WS-1017", "Victoria Sterling-Hart", "victoria.hart@worksight.io", "Chief Financial Officer", "FIN", core_shift, "Desk 2W-01"),
        ("WS-1018", "David Rosen", "david.rosen@worksight.io", "Corporate Privacy Counsel", "FIN", core_shift, "Desk 2W-02"),
        ("WS-1019", "Aisha Patel", "aisha.patel@worksight.io", "Senior Financial Controller", "FIN", core_shift, "Desk 2W-03"),
        ("WS-1020", "Lucas Meyer", "lucas.meyer@worksight.io", "Procurement & Vendor Lead", "FIN", early_shift, "Desk 2W-04"),
        # Client Advisory (4)
        ("WS-1021", "Olivia Bennett", "olivia.bennett@worksight.io", "VP of Client Advisory", "ADV", core_shift, "Desk 1C-01"),
        ("WS-1022", "Gabriel Morales", "gabriel.morales@worksight.io", "Enterprise Solutions Advisor", "ADV", core_shift, "Desk 1C-02"),
        ("WS-1023", "Chloe Park", "chloe.park@worksight.io", "Customer Success Manager", "ADV", flex_shift, "Desk 1C-03"),
        ("WS-1024", "Noah Lindqvist", "noah.lindqvist@worksight.io", "Implementation Consultant", "ADV", core_shift, "Desk 1C-04"),
    ]

    employees = []
    emp_by_email = {}
    for idx, (code, name, email, title, dcode, shift, desk) in enumerate(employees_seed, start=1):
        emp = Employee(
            employee_code=code,
            full_name=name,
            email=email,
            phone=f"+1 (415) 555-{1000 + idx:04d}",
            job_title=title,
            department_id=dept_by_code[dcode].id,
            shift_id=shift.id,
            badge_id=f"CARD-{88000 + idx}",
            employment_status="active",
            hire_date=today - timedelta(days=rng.randint(120, 1100)),
            workspace_desk_label=desk,
            privacy_consent_accepted=True,
            privacy_consent_at=now - timedelta(days=30),
        )
        db.add(emp)
        employees.append(emp)
        emp_by_email[email] = emp
    db.flush()

    # 5. Four Role-Based User Accounts
    demo_pw = get_password_hash("WorkSight2026!")
    users_seed = [
        User(
            email="owner@worksight.io",
            full_name="Eleanor Vance",
            hashed_password=demo_pw,
            role="super_admin",
            can_view_cctv=True,
            employee_id=emp_by_email["owner@worksight.io"].id,
        ),
        User(
            email="hr@worksight.io",
            full_name="Nadia Al-Mansoor",
            hashed_password=demo_pw,
            role="hr_admin",
            can_view_cctv=True,
            employee_id=emp_by_email["hr@worksight.io"].id,
        ),
        User(
            email="manager@worksight.io",
            full_name="Marcus Sterling",
            hashed_password=demo_pw,
            role="dept_manager",
            can_view_cctv=False,
            managed_department_id=dept_by_code["ENG"].id,
            employee_id=emp_by_email["manager@worksight.io"].id,
        ),
        User(
            email="employee@worksight.io",
            full_name="Maya Lin",
            hashed_password=demo_pw,
            role="employee",
            can_view_cctv=False,
            employee_id=emp_by_email["employee@worksight.io"].id,
        ),
    ]
    for u in users_seed:
        db.add(u)
    db.flush()

    hr_user = users_seed[1]
    owner_user = users_seed[0]

    # 6. Leave Requests (some approved covering today, some pending for HR review)
    leave_seeds = [
        (emp_by_email["kenji.takahashi@worksight.io"], "annual", today - timedelta(days=1), today + timedelta(days=2), "Family autumn travel", "approved"),
        (emp_by_email["priya.nair@worksight.io"], "sick", today, today + timedelta(days=1), "Medical recovery day", "approved"),
        (emp_by_email["maya.lin@worksight.io"] if "maya.lin@worksight.io" in emp_by_email else emp_by_email["employee@worksight.io"], "annual", today + timedelta(days=10), today + timedelta(days=12), "Planned personal retreat", "pending"),
        (emp_by_email["arjun.mehta@worksight.io"], "personal", today + timedelta(days=4), today + timedelta(days=5), "Relocation logistics", "pending"),
        (emp_by_email["gabriel.morales@worksight.io"], "annual", today + timedelta(days=7), today + timedelta(days=9), "Annual vacation", "pending"),
    ]
    on_leave_today_ids = set()
    for emp, ltype, sdate, edate, reason, lstatus in leave_seeds:
        days = (edate - sdate).days + 1
        lr = LeaveRequest(
            employee_id=emp.id,
            leave_type=ltype,
            start_date=sdate,
            end_date=edate,
            days_count=days,
            reason=reason,
            status=lstatus,
            reviewed_by_user_id=hr_user.id if lstatus != "pending" else None,
            review_notes="Approved per annual leave allowance." if lstatus == "approved" else None,
            reviewed_at=(now - timedelta(days=2)) if lstatus != "pending" else None,
        )
        db.add(lr)
        if lstatus == "approved" and sdate <= today <= edate:
            on_leave_today_ids.add(emp.id)
            emp.employment_status = "on_leave"

    # 7. 14 Days of Realistic Verified Attendance Records
    methods = ["access_card", "access_card", "qr_code", "web_portal"]
    shift_map = {s.id: s for s in shifts}

    for day_offset in range(13, -1, -1):
        rec_date = today - timedelta(days=day_offset)
        # Skip weekends for realistic corporate rhythm (unless today is weekend, still populate today so dashboard looks rich)
        if rec_date.weekday() >= 5 and day_offset > 0:
            continue

        for idx, emp in enumerate(employees):
            sh = shift_map.get(emp.shift_id, core_shift)
            sh_hour, sh_min = map(int, sh.start_time.split(":"))
            end_hour, end_min = map(int, sh.end_time.split(":"))

            # Today's deterministic rich distribution
            if day_offset == 0:
                if emp.id in on_leave_today_ids:
                    db.add(
                        AttendanceRecord(
                            employee_id=emp.id,
                            attendance_date=rec_date,
                            verification_method="hr_adjusted",
                            record_category="verified_attendance",
                            status="on_leave",
                            working_hours=0.0,
                            notes="Approved leave",
                        )
                    )
                    continue
                if idx in (13, 19):  # 2 absent today
                    db.add(
                        AttendanceRecord(
                            employee_id=emp.id,
                            attendance_date=rec_date,
                            verification_method="access_card",
                            record_category="verified_attendance",
                            status="absent",
                            working_hours=0.0,
                            notes="No verified check-in recorded",
                        )
                    )
                    continue
                is_late = idx in (4, 11, 22)
                is_early = idx in (7, 15)
                in_offset = rng.randint(20, 42) if is_late else rng.randint(-12, 8)
                ci_dt = datetime.combine(rec_date, time(sh_hour, sh_min), tzinfo=timezone.utc) + timedelta(minutes=in_offset)
                # Leave most employees currently checked in; some early departures already checked out
                if is_early:
                    co_dt = datetime.combine(rec_date, time(end_hour, end_min), tzinfo=timezone.utc) - timedelta(minutes=rng.randint(25, 55))
                    hrs = round(max(0.0, (co_dt - ci_dt).total_seconds() / 3600.0), 2)
                    status = "late_and_early" if is_late else "early_departure"
                    early_min = int((datetime.combine(rec_date, time(end_hour, end_min), tzinfo=timezone.utc) - co_dt).total_seconds() // 60)
                else:
                    co_dt = None
                    hrs = round(max(1.5, min(7.8, rng.uniform(4.2, 7.2))), 2)
                    status = "late" if is_late else "present"
                    early_min = 0
                late_min = max(0, in_offset) if is_late else 0
                db.add(
                    AttendanceRecord(
                        employee_id=emp.id,
                        attendance_date=rec_date,
                        check_in_time=ci_dt,
                        check_out_time=co_dt,
                        verification_method=rng.choice(methods),
                        record_category="verified_attendance",
                        status=status,
                        working_hours=hrs,
                        late_minutes=late_min,
                        early_departure_minutes=early_min,
                    )
                )
            else:
                roll = rng.random()
                if roll < 0.06:
                    db.add(
                        AttendanceRecord(
                            employee_id=emp.id,
                            attendance_date=rec_date,
                            verification_method="hr_adjusted",
                            record_category="verified_attendance",
                            status="on_leave",
                            working_hours=0.0,
                        )
                    )
                    continue
                if roll < 0.11:
                    db.add(
                        AttendanceRecord(
                            employee_id=emp.id,
                            attendance_date=rec_date,
                            verification_method="access_card",
                            record_category="verified_attendance",
                            status="absent",
                            working_hours=0.0,
                        )
                    )
                    continue

                late_roll = rng.random() < 0.14
                early_roll = rng.random() < 0.09
                in_offset = rng.randint(18, 45) if late_roll else rng.randint(-15, 10)
                out_offset = -rng.randint(20, 50) if early_roll else rng.randint(-5, 35)
                ci_dt = datetime.combine(rec_date, time(sh_hour, sh_min), tzinfo=timezone.utc) + timedelta(minutes=in_offset)
                co_dt = datetime.combine(rec_date, time(end_hour, end_min), tzinfo=timezone.utc) + timedelta(minutes=out_offset)
                hrs = round(max(0.0, (co_dt - ci_dt).total_seconds() / 3600.0), 2)
                if late_roll and early_roll:
                    st = "late_and_early"
                elif late_roll:
                    st = "late"
                elif early_roll:
                    st = "early_departure"
                else:
                    st = "present"
                db.add(
                    AttendanceRecord(
                        employee_id=emp.id,
                        attendance_date=rec_date,
                        check_in_time=ci_dt,
                        check_out_time=co_dt,
                        verification_method=rng.choice(methods),
                        record_category="verified_attendance",
                        status=st,
                        working_hours=hrs,
                        late_minutes=max(0, in_offset) if late_roll else 0,
                        early_departure_minutes=max(0, -out_offset) if early_roll else 0,
                    )
                )

    db.flush()

    # 8. Attendance Correction Requests
    maya_emp = emp_by_email["employee@worksight.io"]
    arjun_emp = emp_by_email["arjun.mehta@worksight.io"]
    db.add_all(
        [
            AttendanceCorrection(
                employee_id=maya_emp.id,
                attendance_date=today - timedelta(days=2),
                requested_check_in="08:55",
                requested_check_out="17:40",
                reason="Turnstile badge reader did not register morning tap; escorted in with security log.",
                status="pending",
            ),
            AttendanceCorrection(
                employee_id=arjun_emp.id,
                attendance_date=today - timedelta(days=1),
                requested_check_in="09:50",
                requested_check_out="18:35",
                reason="QR check-in failed during Wi-Fi maintenance window.",
                status="pending",
            ),
            AttendanceCorrection(
                employee_id=emp_by_email["claire.beaumont@worksight.io"].id,
                attendance_date=today - timedelta(days=4),
                requested_check_in="09:00",
                requested_check_out="17:30",
                reason="Offsite client architecture review approved by department lead.",
                status="approved",
                reviewed_by_user_id=hr_user.id,
                review_notes="Verified with Engineering Director.",
                reviewed_at=now - timedelta(days=3),
            ),
        ]
    )

    # 9. Clearly Labeled SIMULATED Development Cameras & Monitoring Zones
    cameras_seed = [
        (
            "CAM-01 Main Reception Lobby",
            "Floor 1 — Primary Entrance Turnstiles",
            dept_by_code["ADV"].id,
            "online",
            4,
            12,
            [
                ("Lobby Entry Line", "entry_exit", [[0.08, 0.25], [0.92, 0.25], [0.92, 0.72], [0.08, 0.72]], 12, 60),
                ("Visitor Waiting Lounge", "common_area", [[0.10, 0.74], [0.88, 0.74], [0.88, 0.94], [0.10, 0.94]], 8, 90),
            ],
        ),
        (
            "CAM-02 Engineering North Studio",
            "Floor 3 — Engineering Open Workspace",
            dept_by_code["ENG"].id,
            "online",
            6,
            14,
            [
                ("Core Engineering Desks", "workspace", [[0.08, 0.18], [0.92, 0.18], [0.92, 0.88], [0.08, 0.88]], 14, 45),
            ],
        ),
        (
            "CAM-03 Product & Design Atelier",
            "Floor 3 — South Collaboration Studio",
            dept_by_code["PRD"].id,
            "online",
            4,
            10,
            [
                ("Design Critique Zone", "workspace", [[0.12, 0.20], [0.88, 0.20], [0.88, 0.85], [0.12, 0.85]], 10, 45),
            ],
        ),
        (
            "CAM-04 Data Center & Server Vault",
            "Floor 2 — Restricted Infrastructure Room",
            dept_by_code["ENG"].id,
            "online",
            0,
            2,
            [
                ("Server Rack Restricted Perimeter", "restricted", [[0.15, 0.20], [0.85, 0.20], [0.85, 0.85], [0.15, 0.85]], 2, 180),
            ],
        ),
        (
            "CAM-05 People & Finance Atrium",
            "Floor 2 — Central Operations Corridor",
            dept_by_code["OPS"].id,
            "online",
            5,
            12,
            [
                ("Atrium Workspace Cluster", "workspace", [[0.10, 0.16], [0.90, 0.16], [0.90, 0.86], [0.10, 0.86]], 12, 45),
            ],
        ),
        (
            "CAM-06 East Wing Rooftop Terrace",
            "Floor 4 — Secondary Access Door",
            dept_by_code["FIN"].id,
            "degraded",
            0,
            8,
            [
                ("Terrace Threshold", "entry_exit", [[0.15, 0.22], [0.85, 0.22], [0.85, 0.78], [0.15, 0.78]], 8, 90),
            ],
        ),
    ]

    cameras = []
    zones_by_cam = {}
    for cname, loc, did, status, occ, max_occ, zdefs in cameras_seed:
        cam = Camera(
            name=cname,
            location=loc,
            department_id=did,
            camera_type="simulated",
            is_simulated=True,
            masked_endpoint=f"simulated://dev-feed/{cname.split()[0].lower()} (SIMULATED)",
            status=status,
            resolution="1280x720",
            fps=15.0 if status == "online" else 6.0,
            last_heartbeat_at=now - timedelta(seconds=12 if status == "online" else 185),
            reconnect_attempts=0 if status == "online" else 2,
            current_occupancy=occ,
            max_occupancy_threshold=max_occ,
            ai_enabled=True,
            recording_enabled=False,
        )
        db.add(cam)
        db.flush()
        cameras.append(cam)
        zones_by_cam[cam.id] = []
        for zname, ztype, coords, zmax, zvac in zdefs:
            z = MonitoringZone(
                camera_id=cam.id,
                name=zname,
                zone_type=ztype,
                coordinates_json=json.dumps(coords),
                max_occupancy=zmax,
                vacancy_alert_minutes=zvac,
                is_active=True,
                current_count=occ,
                last_occupied_at=now - timedelta(minutes=5 if occ > 0 else 65),
            )
            db.add(z)
            db.flush()
            zones_by_cam[cam.id].append(z)

    # 10. Realistic AI Vision Telemetry Events (clearly simulated & anonymous)
    expires_at = now + timedelta(days=90)
    events_seed = [
        (cameras[0], zones_by_cam[cameras[0].id][0], "entry", "info", 3, ["trk_0104", "trk_0105", "trk_0106"], 0.94, "Morning entry flow detected across Main Lobby entry line (3 anonymous passages).", 18, "confirmed"),
        (cameras[1], zones_by_cam[cameras[1].id][0], "occupancy_change", "info", 6, ["trk_0201", "trk_0202", "trk_0203", "trk_0204", "trk_0205", "trk_0206"], 0.91, "Engineering North Studio occupancy reached 6 anonymous persons (43% of zone capacity).", 34, "unreviewed"),
        (cameras[3], zones_by_cam[cameras[3].id][0], "restricted_intrusion", "critical", 1, ["trk_0401"], 0.89, "Anonymous person detected inside Server Rack Restricted Perimeter. Verify scheduled IT maintenance ticket.", 52, "unreviewed"),
        (cameras[2], zones_by_cam[cameras[2].id][0], "extended_vacancy", "info", 0, [], 0.98, "Design Critique Zone unoccupied for 58 minutes (spatial utilization metric only; not a productivity assessment).", 95, "resolved"),
        (cameras[4], zones_by_cam[cameras[4].id][0], "crowd_detected", "warning", 13, ["trk_0501", "trk_0502", "trk_0503"], 0.88, "Atrium Workspace Cluster briefly exceeded threshold (13 observed vs limit 12) during all-hands gathering.", 140, "confirmed"),
        (cameras[5], None, "camera_disconnected", "warning", 0, [], 1.0, "East Wing Rooftop Terrace feed experienced packet drop; automatic reconnection backoff active.", 24, "unreviewed"),
        (cameras[0], zones_by_cam[cameras[0].id][0], "exit", "info", 2, ["trk_0112", "trk_0113"], 0.92, "Exit transition detected across Main Lobby entry line (2 anonymous passages).", 11, "unreviewed"),
    ]
    created_events = []
    for cam, z, etype, sev, pcnt, tids, conf, desc, mins_ago, rstatus in events_seed:
        ev = VisionEvent(
            camera_id=cam.id,
            zone_id=z.id if z else None,
            event_type=etype,
            source_category="ai_presence_telemetry",
            severity=sev,
            person_count=pcnt,
            anonymous_track_ids_json=json.dumps(tids),
            confidence=conf,
            description=desc,
            is_simulated=True,
            review_status=rstatus,
            reviewed_by_user_id=hr_user.id if rstatus != "unreviewed" else None,
            review_notes="Reviewed and logged by Workplace Operations." if rstatus != "unreviewed" else None,
            reviewed_at=(now - timedelta(minutes=max(1, mins_ago - 5))) if rstatus != "unreviewed" else None,
            occurred_at=now - timedelta(minutes=mins_ago),
            expires_at=expires_at,
        )
        db.add(ev)
        db.flush()
        created_events.append(ev)

    # 11. Notifications
    notifs_seed = [
        ("Restricted Zone Alert — Server Vault", "Anonymous person detected inside Server Rack Restricted Perimeter on CAM-04. Please review against IT access logs.", "restricted_area", "critical", "super_admin,hr_admin", dept_by_code["ENG"].id, created_events[2].id, False, "pending"),
        ("Camera Stream Degraded — CAM-06", "East Wing Rooftop Terrace experienced stream interruption. Reconnection attempt #2 in progress.", "camera", "warning", "super_admin,hr_admin", dept_by_code["FIN"].id, created_events[5].id, False, "pending"),
        ("Pending Attendance Corrections (2)", "Maya Lin and Arjun Mehta submitted attendance correction requests awaiting HR review.", "attendance", "info", "super_admin,hr_admin,dept_manager", dept_by_code["ENG"].id, None, False, "pending"),
        ("Atrium Occupancy Threshold Exceeded", "Atrium Workspace Cluster briefly reached 13/12 capacity during morning briefing.", "occupancy", "warning", "super_admin,hr_admin", dept_by_code["OPS"].id, created_events[4].id, True, "acknowledged"),
        ("Leave Requests Awaiting Review", "3 employee leave applications are pending manager/HR approval.", "leave", "info", "super_admin,hr_admin,dept_manager", None, None, False, "pending"),
    ]
    for title, msg, cat, sev, roles, did, ev_id, is_read, rstat in notifs_seed:
        db.add(
            Notification(
                title=title,
                message=msg,
                category=cat,
                severity=sev,
                target_roles=roles,
                department_id=did,
                related_event_id=ev_id,
                is_read=is_read,
                review_status=rstat,
                created_at=now - timedelta(minutes=rng.randint(10, 120)),
            )
        )

    # 12. Initial Audit Logs
    db.add_all(
        [
            AuditLog(
                user_id=owner_user.id,
                user_email=owner_user.email,
                user_role=owner_user.role,
                action="privacy_policy_published",
                resource_type="retention_policy",
                resource_id="1",
                details="Published WorkSight Transparent Monitoring Policy v2026.1 (raw video storage disabled).",
                ip_address="127.0.0.1",
                created_at=now - timedelta(hours=18),
            ),
            AuditLog(
                user_id=hr_user.id,
                user_email=hr_user.email,
                user_role=hr_user.role,
                action="attendance_correction_approved",
                resource_type="attendance_correction",
                resource_id="3",
                details="Approved offsite architecture review attendance correction for Claire Beaumont.",
                ip_address="127.0.0.1",
                created_at=now - timedelta(hours=5),
            ),
            AuditLog(
                user_id=owner_user.id,
                user_email=owner_user.email,
                user_role=owner_user.role,
                action="retention_purge_executed",
                resource_type="retention_policy",
                resource_id="1",
                details="Scheduled privacy retention sweep removed 14 expired metadata entries.",
                ip_address="127.0.0.1",
                created_at=now - timedelta(hours=6),
            ),
        ]
    )

    db.commit()
