"""CCTV Credential Encryption, Zero-Leakage, Stream Audit & Retention Purge Tests."""

from app.core.security import decrypt_secret, encrypt_secret


def test_fernet_credential_encryption_roundtrip():
    secret_uri = "rtsp://admin:SuperSecret99!@192.168.1.50:554/stream1"
    encrypted = encrypt_secret(secret_uri)
    assert encrypted is not None
    assert "SuperSecret99!" not in encrypted
    assert "192.168.1.50" not in encrypted
    assert decrypt_secret(encrypted) == secret_uri


def test_camera_api_never_exposes_rtsp_credentials(client, owner_headers):
    create_resp = client.post(
        "/api/cameras",
        headers=owner_headers,
        json={
            "name": "Test RTSP Gate Cam",
            "location": "Loading Dock",
            "camera_type": "rtsp",
            "is_simulated": False,
            "rtsp_url": "rtsp://192.168.50.10:554/h264Preview_01_main",
            "username": "sec_operator",
            "password": "TopSecretPassword123",
            "max_occupancy_threshold": 6,
            "ai_enabled": True,
            "recording_enabled": False,
        },
    )
    assert create_resp.status_code == 201
    body_text = create_resp.text
    assert "TopSecretPassword123" not in body_text
    assert "sec_operator" not in body_text
    assert "h264Preview_01_main" not in body_text

    data = create_resp.json()
    assert "***" in data["masked_endpoint"]
    cam_id = data["id"]

    # Clean up created camera
    del_resp = client.delete(f"/api/cameras/{cam_id}", headers=owner_headers)
    assert del_resp.status_code == 200


def test_stream_token_snapshot_and_audit_trail(client, owner_headers):
    cams = client.get("/api/cameras", headers=owner_headers).json()
    assert len(cams) > 0
    sim_cam = next(c for c in cams if c["is_simulated"])

    token_resp = client.post(
        f"/api/cameras/{sim_cam['id']}/stream-token", headers=owner_headers
    )
    assert token_resp.status_code == 200
    snap_url = token_resp.json()["snapshot_url"]

    snap = client.get(snap_url)
    assert snap.status_code == 200
    assert snap.headers["content-type"] == "image/jpeg"
    assert snap.content[:2] == b"\xff\xd8"  # Valid JPEG header

    # Verify access audit log recorded the stream access
    logs = client.get("/api/settings/audit-logs?action=cctv_live_stream_accessed", headers=owner_headers)
    assert logs.status_code == 200
    assert len(logs.json()) >= 1


def test_retention_purge_endpoint(client, owner_headers):
    resp = client.post("/api/settings/run-retention", headers=owner_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "deleted_events" in body
    assert "deleted_files" in body
