import pytest
from backend.app import create_app
from backend.app.db.migrate import main as run_migrations
from backend.app.db.seed import seed_database
from backend.app.db.connection import get_db, fetch_one, execute_query

@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config["TESTING"] = True
    run_migrations()
    seed_database()
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"]["connected"] is True
    assert data["database"]["volunteer_profiles_count"] > 0

def test_auth_login_convener_and_co_convener(client):
    # Convener login
    res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    assert res.status_code == 200
    convener_data = res.get_json()["data"]
    assert convener_data["user"]["role"] == "convener"
    assert "token" in convener_data

    # Co-convener login
    res = client.post("/api/v1/auth/login", json={"email": "coconvener@tapmi.edu.in", "password": "coconvener123"})
    assert res.status_code == 200
    coconvener_data = res.get_json()["data"]
    assert coconvener_data["user"]["role"] == "co_convener"

def test_unauthenticated_protected_route_fails(client):
    res = client.get("/api/v1/volunteers")
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHENTICATED"

def test_volunteer_forbidden_from_organizer_endpoints(client):
    # Log in as pre-seeded volunteer V001
    with get_db() as conn:
        v = fetch_one(conn, "SELECT email FROM volunteer_profiles WHERE student_id = 'V001'")
        email = v["email"]

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "volunteer123"})
    assert res.status_code == 200
    vol_token = res.get_json()["data"]["token"]

    # Try accessing organizer endpoint /volunteers
    res = client.get("/api/v1/volunteers", headers={"Authorization": f"Bearer {vol_token}"})
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "FORBIDDEN"

def test_duplicate_student_id_and_email_rejected(client):
    # Log in as convener
    res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    token = res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate student ID V001
    res = client.post("/api/v1/volunteers", json={
        "full_name": "Duplicate Student",
        "student_id": "V001",
        "email": "unique.email999@tapmi.edu.in"
    }, headers=headers)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "DUPLICATE_STUDENT_ID"

    # Duplicate email
    res = client.post("/api/v1/volunteers", json={
        "full_name": "Duplicate Email",
        "student_id": "V999",
        "email": "convener@tapmi.edu.in"
    }, headers=headers)
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "DUPLICATE_EMAIL"

def test_volunteer_activation_otp_workflow(client):
    import time
    unique_suffix = str(int(time.time()))[-4:]
    test_sid = f"V{unique_suffix}"
    test_email = f"onboarding.{test_sid.lower()}@tapmi.edu.in"

    # Convener creates new volunteer
    login_res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    token = login_res.get_json()["data"]["token"]

    res = client.post("/api/v1/volunteers", json={
        "full_name": "Test Onboarding Volunteer",
        "student_id": test_sid,
        "email": test_email
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201

    # Request activation OTP
    req_res = client.post("/api/v1/auth/activation/request", json={
        "student_id": test_sid,
        "email": test_email
    })
    assert req_res.status_code == 200

    # Fetch generated OTP from database challenge row for test verification
    with get_db() as conn:
        vol = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE student_id = %s", (test_sid,))
        ch = fetch_one(conn, "SELECT * FROM otp_challenges WHERE volunteer_profile_id = %s", (vol["id"],))
        assert ch is not None

    # Test invalid OTP rejected
    verify_bad = client.post("/api/v1/auth/activation/verify", json={
        "student_id": test_sid,
        "email": test_email,
        "otp": "000000"
    })
    assert verify_bad.status_code == 400

    # Re-insert known hash to simulate exact OTP entry
    from backend.app.services.auth_service import hash_otp
    known_otp = "123456"
    with get_db() as conn:
        execute_query(conn, "UPDATE otp_challenges SET otp_hash = %s, attempt_count = 0 WHERE id = %s", (hash_otp(known_otp), ch["id"]))
        conn.commit()

    verify_ok = client.post("/api/v1/auth/activation/verify", json={
        "student_id": test_sid,
        "email": test_email,
        "otp": known_otp
    })
    assert verify_ok.status_code == 200
    assert "ticket" in verify_ok.get_json()["data"]

    # Complete activation by setting password
    comp_res = client.post("/api/v1/auth/activation/complete", json={
        "student_id": test_sid,
        "email": test_email,
        "password": "mypassword123"
    })
    assert comp_res.status_code == 200

    # Now verify the activated volunteer can log in with their password
    new_login = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "mypassword123"
    })
    assert new_login.status_code == 200
    assert new_login.get_json()["data"]["user"]["role"] == "volunteer"
