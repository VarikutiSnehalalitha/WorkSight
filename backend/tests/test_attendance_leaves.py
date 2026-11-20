"""Attendance Check-In/Out, Correction Approval, Leave Workflow & Report Export Tests."""

from datetime import date, timedelta


def test_employee_attendance_only_returns_own_records(client, employee_headers):
    me = client.get("/api/auth/me", headers=employee_headers).json()
    resp = client.get("/api/attendance", headers=employee_headers)
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) > 0
    assert all(r["employee_id"] == me["employee_id"] for r in records)
    assert all(r["record_category"] == "verified_attendance" for r in records)


def test_correction_request_and_hr_approval_workflow(client, employee_headers, hr_headers):
    target_day = (date.today() - timedelta(days=5)).isoformat()
    create_resp = client.post(
        "/api/attendance/corrections",
        headers=employee_headers,
        json={
            "attendance_date": target_day,
            "requested_check_in": "08:55",
            "requested_check_out": "17:35",
            "reason": "Access card reader offline during morning entry.",
        },
    )
    assert create_resp.status_code == 201
    corr_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "pending"

    # Employee cannot approve their own correction
    self_approve = client.post(
        f"/api/attendance/corrections/{corr_id}/review",
        headers=employee_headers,
        json={"status": "approved", "review_notes": "Self"},
    )
    assert self_approve.status_code == 403

    # HR approves correction
    review_resp = client.post(
        f"/api/attendance/corrections/{corr_id}/review",
        headers=hr_headers,
        json={"status": "approved", "review_notes": "Verified with lobby desk log."},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"


def test_leave_application_and_hr_review(client, employee_headers, hr_headers):
    sdate = (date.today() + timedelta(days=20)).isoformat()
    edate = (date.today() + timedelta(days=21)).isoformat()
    resp = client.post(
        "/api/leaves",
        headers=employee_headers,
        json={
            "leave_type": "annual",
            "start_date": sdate,
            "end_date": edate,
            "reason": "Scheduled family trip.",
        },
    )
    assert resp.status_code == 201
    leave_id = resp.json()["id"]
    assert resp.json()["days_count"] == 2

    approve = client.post(
        f"/api/leaves/{leave_id}/review",
        headers=hr_headers,
        json={"status": "approved", "review_notes": "Approved."},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"


def test_excel_and_pdf_report_exports(client, hr_headers):
    excel = client.get("/api/reports/export/excel", headers=hr_headers)
    assert excel.status_code == 200
    assert "spreadsheetml" in excel.headers["content-type"]
    assert excel.content[:2] == b"PK"  # Valid ZIP/XLSX signature

    pdf = client.get("/api/reports/export/pdf", headers=hr_headers)
    assert pdf.status_code == 200
    assert "application/pdf" in pdf.headers["content-type"]
    assert pdf.content[:4] == b"%PDF"
