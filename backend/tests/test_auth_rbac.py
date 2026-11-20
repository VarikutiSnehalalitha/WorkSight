"""Strict Role-Based Access Control (RBAC) & Authentication Tests."""


def test_health_endpoint_declares_ethical_guardrails(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["ethical_guardrails"]["facial_recognition"] is False
    assert data["ethical_guardrails"]["emotion_recognition"] is False
    assert data["ethical_guardrails"]["automated_productivity_scoring"] is False
    assert data["ethical_guardrails"]["human_review_required"] is True


def test_employee_blocked_from_admin_hr_and_cctv_routes(client, employee_headers):
    forbidden_paths = [
        "/api/dashboard/overview",
        "/api/employees",
        "/api/departments",
        "/api/cameras",
        "/api/events",
        "/api/reports/summary",
        "/api/settings/retention",
        "/api/settings/audit-logs",
        "/api/settings/user-access",
    ]
    for path in forbidden_paths:
        resp = client.get(path, headers=employee_headers)
        assert resp.status_code == 403, f"Employee should be blocked from {path}, got {resp.status_code}"


def test_employee_can_access_self_service_and_monitoring_policy(client, employee_headers):
    me = client.get("/api/auth/me", headers=employee_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "employee"

    self_dash = client.get("/api/dashboard/employee-self", headers=employee_headers)
    assert self_dash.status_code == 200
    assert self_dash.json()["employee"]["email"] == "employee@worksight.io"

    policy = client.get("/api/auth/monitoring-policy", headers=employee_headers)
    assert policy.status_code == 200
    assert len(policy.json()["prohibited_practices"]) >= 5


def test_department_manager_scoped_to_assigned_department_only(client, manager_headers, owner_headers):
    # Manager cannot access CCTV or global settings
    assert client.get("/api/cameras", headers=manager_headers).status_code == 403
    assert client.get("/api/settings/retention", headers=manager_headers).status_code == 403

    # Manager only sees their assigned department (Engineering)
    mgr_depts = client.get("/api/departments", headers=manager_headers)
    assert mgr_depts.status_code == 200
    depts = mgr_depts.json()
    assert len(depts) == 1
    assert depts[0]["code"] == "ENG"

    # Attempting to query another department returns 403
    all_depts = client.get("/api/departments", headers=owner_headers).json()
    other_dept = next(d for d in all_depts if d["code"] != "ENG")
    forbidden_emp = client.get(
        f"/api/employees?department_id={other_dept['id']}", headers=manager_headers
    )
    assert forbidden_emp.status_code == 403


def test_super_admin_and_hr_can_access_overview_and_reports(client, owner_headers, hr_headers):
    for headers in (owner_headers, hr_headers):
        overview = client.get("/api/dashboard/overview", headers=headers)
        assert overview.status_code == 200
        body = overview.json()
        assert body["total_employees"] >= 20
        assert body["ethics_disclosure"]["presence_is_not_productivity"] is True
        assert body["ethics_disclosure"]["facial_recognition_enabled"] is False
