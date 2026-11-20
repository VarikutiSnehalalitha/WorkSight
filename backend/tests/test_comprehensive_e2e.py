"""Comprehensive End-to-End System, API, and Governance Test Suite for WorkSight."""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient


def test_department_crud_and_metrics(client, owner_headers):
    # 1. Create a new test department
    create_payload = {
        "name": "Quality Assurance & Testing",
        "code": "QAT",
        "floor_location": "Floor 3 — East Lab",
        "description": "Validation and test automation engineers.",
        "target_capacity": 10,
    }
    create_resp = client.post("/api/departments", headers=owner_headers, json=create_payload)
    assert create_resp.status_code == 201, f"Create department failed: {create_resp.text}"
    dept_data = create_resp.json()
    dept_id = dept_data["id"]
    assert dept_data["name"] == "Quality Assurance & Testing"
    assert dept_data["code"] == "QAT"
    assert dept_data["target_capacity"] == 10

    # 2. Update department
    update_payload = {
        "floor_location": "Floor 3 — West Lab",
        "target_capacity": 15,
    }
    update_resp = client.put(f"/api/departments/{dept_id}", headers=owner_headers, json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["floor_location"] == "Floor 3 — West Lab"
    assert update_resp.json()["target_capacity"] == 15

    # 3. Retrieve list and verify QAT is present with valid calculated metrics
    list_resp = client.get("/api/departments", headers=owner_headers)
    assert list_resp.status_code == 200
    depts = list_resp.json()
    found = next((d for d in depts if d["id"] == dept_id), None)
    assert found is not None
    assert "attendance_rate" in found
    assert "present_today" in found
    assert "ai_observed_occupancy" in found


def test_employee_crud_and_search_filters(client, owner_headers):
    # 1. Get an existing department
    depts = client.get("/api/departments", headers=owner_headers).json()
    target_dept = depts[0]["id"]

    # 2. Create employee
    new_emp_payload = {
        "employee_code": "WS-TEST-99",
        "full_name": "Seraphina Vance",
        "email": "seraphina.vance@worksight.io",
        "phone": "+1 (415) 555-8888",
        "job_title": "Platform Quality Lead",
        "department_id": target_dept,
        "workspace_desk_label": "Desk 3W-99",
    }
    res = client.post("/api/employees", headers=owner_headers, json=new_emp_payload)
    assert res.status_code == 201, f"Failed creating employee: {res.text}"
    emp = res.json()
    emp_id = emp["id"]
    assert emp["employee_code"] == "WS-TEST-99"
    assert emp["full_name"] == "Seraphina Vance"
    assert emp["badge_id"] == "CARD-WS-TEST-99"

    # 3. Search for the employee
    search_res = client.get("/api/employees?search=Seraphina", headers=owner_headers)
    assert search_res.status_code == 200
    found_emps = search_res.json()
    assert len(found_emps) == 1
    assert found_emps[0]["id"] == emp_id

    # 4. Update employee
    up_res = client.put(
        f"/api/employees/{emp_id}",
        headers=owner_headers,
        json={"job_title": "Senior Platform Quality Lead", "workspace_desk_label": "Desk 3W-100"},
    )
    assert up_res.status_code == 200
    assert up_res.json()["job_title"] == "Senior Platform Quality Lead"

    # 5. Deactivate employee
    del_res = client.delete(f"/api/employees/{emp_id}", headers=owner_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deactivated"


def test_attendance_shift_and_duplicate_handling(client, owner_headers, employee_headers):
    # 1. Employee checks in
    ci_resp = client.post(
        "/api/attendance/check-in",
        headers=employee_headers,
        json={"verification_method": "qr_code", "notes": "E2E automated check-in"},
    )
    # Could be 200 (if not checked in today) or 400 (if already checked in during test seed)
    if ci_resp.status_code == 200:
        rec = ci_resp.json()
        assert rec["verification_method"] == "qr_code"
        assert rec["record_category"] == "verified_attendance"
        assert rec["check_in_time"] is not None

        # Attempting duplicate check-in must fail with 400
        dup_resp = client.post(
            "/api/attendance/check-in",
            headers=employee_headers,
            json={"verification_method": "qr_code"},
        )
        assert dup_resp.status_code == 400
        assert "already recorded" in dup_resp.json()["detail"].lower()

    # 2. Check out
    co_resp = client.post(
        "/api/attendance/check-out",
        headers=employee_headers,
        json={"verification_method": "qr_code", "notes": "E2E automated check-out"},
    )
    assert co_resp.status_code in (200, 400)


def test_ai_vision_events_and_notification_workflow(client, owner_headers, hr_headers):
    # 1. Get a camera
    cams = client.get("/api/cameras", headers=owner_headers).json()
    assert len(cams) > 0
    cam = cams[0]

    # 2. Simulate critical restricted-area intrusion event
    sim_resp = client.post(
        "/api/events/simulate",
        headers=owner_headers,
        json={
            "camera_id": cam["id"],
            "event_type": "restricted_intrusion",
            "person_count": 1,
        },
    )
    assert sim_resp.status_code == 201, f"Event simulation failed: {sim_resp.text}"
    ev = sim_resp.json()
    assert ev["severity"] == "critical"
    assert ev["is_simulated"] is True
    assert ev["review_status"] == "unreviewed"
    ev_id = ev["id"]

    # 3. Check notifications list contains this critical notification
    notifs_resp = client.get("/api/notifications?category=restricted_area", headers=hr_headers)
    assert notifs_resp.status_code == 200
    notifs = notifs_resp.json()
    matching_notif = next((n for n in notifs if n.get("related_event_id") == ev_id), None)
    assert matching_notif is not None
    assert matching_notif["severity"] == "critical"
    notif_id = matching_notif["id"]

    # 4. Human-in-the-loop review of the AI event -> mark as resolved
    review_resp = client.post(
        f"/api/events/{ev_id}/review",
        headers=hr_headers,
        json={
            "review_status": "resolved",
            "review_notes": "Security verified authorized IT technician badge entry.",
        },
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["review_status"] == "resolved"

    # 5. Verify the linked notification is automatically resolved
    notif_check = client.get("/api/notifications", headers=hr_headers).json()
    updated_notif = next((n for n in notif_check if n["id"] == notif_id), None)
    assert updated_notif is not None
    assert updated_notif["review_status"] == "resolved"


def test_camera_management_zones_and_stream(client, owner_headers):
    # 1. Create a simulated camera
    cam_resp = client.post(
        "/api/cameras",
        headers=owner_headers,
        json={
            "name": "E2E Lab Test Camera",
            "location": "QA Floor 3 Testing Sandbox",
            "camera_type": "simulated",
            "is_simulated": True,
            "max_occupancy_threshold": 8,
            "ai_enabled": True,
            "recording_enabled": False,
        },
    )
    assert cam_resp.status_code == 201
    cam = cam_resp.json()
    cam_id = cam["id"]
    assert cam["is_simulated"] is True
    assert "SIMULATED" in cam["masked_endpoint"]

    # 2. Add a monitoring zone
    zone_resp = client.post(
        f"/api/cameras/{cam_id}/zones",
        headers=owner_headers,
        json={
            "name": "E2E Workspace Zone",
            "zone_type": "workspace",
            "coordinates": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
            "max_occupancy": 6,
            "vacancy_alert_minutes": 30,
        },
    )
    assert zone_resp.status_code == 201
    zone = zone_resp.json()
    zone_id = zone["id"]
    assert zone["name"] == "E2E Workspace Zone"
    assert zone["max_occupancy"] == 6

    # 3. Test connection on saved camera
    test_conn = client.post(f"/api/cameras/{cam_id}/test", headers=owner_headers)
    assert test_conn.status_code == 200
    assert test_conn.json()["reachable"] is True

    # 4. Generate stream token and fetch snapshot
    token_resp = client.post(f"/api/cameras/{cam_id}/stream-token", headers=owner_headers)
    assert token_resp.status_code == 200
    token = token_resp.json()["stream_token"]

    snap_resp = client.get(f"/api/cameras/{cam_id}/snapshot?token={token}")
    assert snap_resp.status_code == 200
    assert snap_resp.headers["content-type"] == "image/jpeg"

    # 5. Delete zone and camera
    del_zone = client.delete(f"/api/cameras/{cam_id}/zones/{zone_id}", headers=owner_headers)
    assert del_zone.status_code == 200
    del_cam = client.delete(f"/api/cameras/{cam_id}", headers=owner_headers)
    assert del_cam.status_code == 200


def test_user_cctv_access_governance_guardrails(client, owner_headers, hr_headers, employee_headers):
    # 1. Super admin can view user access controls
    users_resp = client.get("/api/settings/user-access", headers=owner_headers)
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert len(users) >= 4

    # 2. HR Admin is prohibited from modifying user access controls (Owner only)
    hr_attempt = client.get("/api/settings/user-access", headers=hr_headers)
    assert hr_attempt.status_code == 403

    # 3. Attempting to grant CCTV access to an Employee role is strictly rejected by privacy policy
    emp_user = next(u for u in users if u["role"] == "employee")
    grant_emp = client.patch(
        f"/api/settings/user-access/{emp_user['id']}",
        headers=owner_headers,
        json={"can_view_cctv": True},
    )
    assert grant_emp.status_code == 400
    assert "privacy guardrail" in grant_emp.json()["detail"].lower()


def test_websocket_authentication_and_protocol(client):
    # 1. Login to obtain access token
    login_resp = client.post(
        "/api/auth/login", json={"email": "owner@worksight.io", "password": "WorkSight2026!"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. Connect with valid token
    with client.websocket_connect(f"/ws?token={token}") as ws:
        # First message is connection confirmation
        greeting = ws.receive_json()
        assert greeting["type"] == "connected"
        assert greeting["payload"]["role"] == "super_admin"

        # Test ping-pong
        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["type"] == "pong"
