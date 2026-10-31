from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import generate_password_hash

from backend.app import create_app
from backend.app.config import Config
from backend.app.db.connection import execute_query, fetch_one, run_migrations, transaction


@pytest.fixture
def core_committee_client(tmp_path, monkeypatch):
    database_path = tmp_path / "core_committee_test.db"
    monkeypatch.setattr(Config, "DATABASE_URL", f"sqlite:///{database_path}")
    run_migrations()

    app = create_app()
    app.config["TESTING"] = True
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    start = (now + timedelta(days=14)).isoformat()
    end = (now + timedelta(days=14, hours=8)).isoformat()

    with transaction() as conn:
        execute_query(conn, """
            INSERT INTO users (email, password_hash, role, status, created_at, updated_at)
            VALUES (%s, %s, 'convener', 'active', %s, %s)
        """, ("convener@test.tapmi.edu.in", generate_password_hash("convener-test-password"), timestamp, timestamp))
        convener = fetch_one(conn, "SELECT id FROM users WHERE email = %s", ("convener@test.tapmi.edu.in",))

        execute_query(conn, """
            INSERT INTO events (name, description, starts_at, ends_at, venue, status, created_by, updated_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'upcoming', %s, %s, %s, %s)
        """, ("Core Committee Test Event", "Test event details", start, end, "TAPMI Auditorium", convener["id"], convener["id"], timestamp, timestamp))
        event = fetch_one(conn, "SELECT id FROM events WHERE name = %s", ("Core Committee Test Event",))

        department_ids = []
        for department_name in ("Stage", "Hospitality"):
            execute_query(conn, "INSERT INTO departments (name, description, active) VALUES (%s, %s, 1)", (department_name, "Test department"))
            department = fetch_one(conn, "SELECT id FROM departments WHERE name = %s", (department_name,))
            department_ids.append(department["id"])
            execute_query(conn, """
                INSERT INTO event_requirements (
                    event_id, department_id, role_name, headcount, priority,
                    requirement_source, created_at, updated_at
                ) VALUES (%s, %s, %s, 1, 'normal', 'fixed_headcount', %s, %s)
            """, (event["id"], department["id"], f"{department_name} Volunteer", timestamp, timestamp))

        volunteers = []
        for student_id, full_name, email in (
            ("T001", "Aarohi Volunteer", "aarohi@test.tapmi.edu.in"),
            ("T002", "Aninjay Volunteer", "aninjay@test.tapmi.edu.in"),
        ):
            execute_query(conn, """
                INSERT INTO volunteer_profiles (student_id, full_name, email, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (student_id, full_name, email, timestamp, timestamp))
            volunteer = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE student_id = %s", (student_id,))
            volunteers.append(volunteer["id"])

        execute_query(conn, """
            INSERT INTO allocation_versions (event_id, version_number, status, created_by, created_at, updated_at)
            VALUES (%s, 1, 'published', %s, %s, %s)
        """, (event["id"], convener["id"], timestamp, timestamp))
        version = fetch_one(conn, "SELECT id FROM allocation_versions WHERE event_id = %s", (event["id"],))
        execute_query(conn, """
            INSERT INTO published_allocations (event_id, allocation_version_id, published_by, published_at)
            VALUES (%s, %s, %s, %s)
        """, (event["id"], version["id"], convener["id"], timestamp))

        for index, volunteer_id in enumerate(volunteers):
            requirement = fetch_one(conn, """
                SELECT id FROM event_requirements WHERE event_id = %s AND department_id = %s
            """, (event["id"], department_ids[index]))
            execute_query(conn, """
                INSERT INTO assignments (
                    allocation_version_id, requirement_id, volunteer_id, assigned_by,
                    assignment_source, created_at
                ) VALUES (%s, %s, %s, %s, 'manual', %s)
            """, (version["id"], requirement["id"], volunteer_id, convener["id"], timestamp))

    with app.test_client() as client:
        yield client, event["id"], department_ids


def login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.get_json()["data"]


def test_convener_creates_core_accounts_and_members_only_see_their_department_roster(core_committee_client):
    client, event_id, department_ids = core_committee_client
    convener = login(client, "convener@test.tapmi.edu.in", "convener-test-password")
    convener_headers = {"Authorization": f"Bearer {convener['token']}"}

    first = client.post("/api/v1/core-committee/members", json={
        "full_name": "Maya Head",
        "email": "maya.head@test.tapmi.edu.in",
        "password": "maya-test-password"
    }, headers=convener_headers)
    second = client.post("/api/v1/core-committee/members", json={
        "full_name": "Ravi Head",
        "email": "ravi.head@test.tapmi.edu.in",
        "password": "ravi-test-password"
    }, headers=convener_headers)
    assert first.status_code == 201
    assert second.status_code == 201
    first_member_id = first.get_json()["data"]["id"]
    second_member_id = second.get_json()["data"]["id"]

    duplicate_head = client.put(f"/api/v1/events/{event_id}/department-heads", json={
        "assignments": [
            {"department_id": department_ids[0], "user_id": first_member_id},
            {"department_id": department_ids[1], "user_id": first_member_id}
        ]
    }, headers=convener_headers)
    assert duplicate_head.status_code == 422
    assert duplicate_head.get_json()["error"]["code"] == "CORE_MEMBER_ALREADY_ASSIGNED"

    saved = client.put(f"/api/v1/events/{event_id}/department-heads", json={
        "assignments": [
            {"department_id": department_ids[0], "user_id": first_member_id},
            {"department_id": department_ids[1], "user_id": second_member_id}
        ]
    }, headers=convener_headers)
    assert saved.status_code == 200

    first_login = login(client, "maya.head@test.tapmi.edu.in", "maya-test-password")
    assert first_login["user"]["role"] == "core_committee"
    first_assignments = client.get("/api/v1/me/department-assignments", headers={
        "Authorization": f"Bearer {first_login['token']}"
    })
    assert first_assignments.status_code == 200
    first_event = first_assignments.get_json()["data"][0]
    assert first_event["event_name"] == "Core Committee Test Event"
    assert first_event["venue"] == "TAPMI Auditorium"
    assert len(first_event["departments"]) == 1
    assert first_event["departments"][0]["department_name"] == "Stage"
    assert first_event["departments"][0]["volunteers"][0]["email"] == "aarohi@test.tapmi.edu.in"

    forbidden = client.get("/api/v1/core-committee/members", headers={
        "Authorization": f"Bearer {first_login['token']}"
    })
    assert forbidden.status_code == 403


def test_department_head_assignments_require_a_published_roster(core_committee_client):
    client, event_id, department_ids = core_committee_client
    with transaction() as conn:
        execute_query(conn, "DELETE FROM published_allocations WHERE event_id = %s", (event_id,))
    convener = login(client, "convener@test.tapmi.edu.in", "convener-test-password")
    headers = {"Authorization": f"Bearer {convener['token']}"}
    response = client.put(f"/api/v1/events/{event_id}/department-heads", json={
        "assignments": [
            {"department_id": department_ids[0], "user_id": None},
            {"department_id": department_ids[1], "user_id": None}
        ]
    }, headers=headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "PUBLISHED_ROSTER_REQUIRED"
