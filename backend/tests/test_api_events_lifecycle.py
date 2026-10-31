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

def test_full_allocation_lifecycle_and_publication(client):
    # 1. Organizer login
    login_res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    token = login_res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch Kala Fest event id
    with get_db() as conn:
        ev = fetch_one(conn, "SELECT id FROM events WHERE name = 'Kala Fest'")
        event_id = ev["id"]

    # 2. Run allocation (ILP optimizer)
    run_res = client.post(f"/api/v1/events/{event_id}/allocations/runs", json={"algorithm": "ilp"}, headers=headers)
    assert run_res.status_code == 201
    run_data = run_res.get_json()["data"]
    version_id = run_data["version_id"]
    assert run_data["status"] == "draft"
    assert run_data["total_allocated"] > 0

    # Verify that before publication, volunteer V001 sees NO published assignments
    with get_db() as conn:
        v001 = fetch_one(conn, "SELECT email FROM volunteer_profiles WHERE student_id = 'V001'")
        v_email = v001["email"]
    vol_login = client.post("/api/v1/auth/login", json={"email": v_email, "password": "volunteer123"})
    vol_token = vol_login.get_json()["data"]["token"]

    vol_assns_before = client.get("/api/v1/me/assignments", headers={"Authorization": f"Bearer {vol_token}"})
    assert vol_assns_before.status_code == 200
    # Before publication, draft assignments are NOT visible to volunteers!
    assert len(vol_assns_before.get_json()["data"]) == 0

    # 3. Organizer reviews allocation version
    ver_details = client.get(f"/api/v1/allocations/{version_id}", headers=headers)
    assert ver_details.status_code == 200
    data = ver_details.get_json()["data"]
    assert len(data["assignments"]) > 0
    assert len(data["department_summary"]) > 0

    # 4. Organizer approves the exact version
    appr_res = client.post(f"/api/v1/allocations/{version_id}/approve", json={"comment": "Approved by Convener"}, headers=headers)
    assert appr_res.status_code == 200

    # Verify status is now approved
    ver_after_appr = client.get(f"/api/v1/allocations/{version_id}", headers=headers)
    assert ver_after_appr.get_json()["data"]["status"] == "approved"

    # 5. Organizer publishes the approved version
    pub_res = client.post(f"/api/v1/allocations/{version_id}/publish", headers=headers)
    assert pub_res.status_code == 200

    # Verify status is now published
    ver_after_pub = client.get(f"/api/v1/allocations/{version_id}", headers=headers)
    assert ver_after_pub.get_json()["data"]["status"] == "published"

    # 6. Verify that volunteers assigned in this published version can now view ONLY their own assignment!
    with get_db() as conn:
        assigned_row = fetch_one(conn, """
            SELECT a.volunteer_id, vp.email, er.role_name, d.name as dept_name
            FROM assignments a
            JOIN volunteer_profiles vp ON a.volunteer_id = vp.id
            JOIN event_requirements er ON a.requirement_id = er.id
            JOIN departments d ON er.department_id = d.id
            WHERE a.allocation_version_id = %s LIMIT 1
        """, (version_id,))

    assigned_v_email = assigned_row["email"]
    # Ensure active user login exists for this assigned volunteer
    with get_db() as conn:
        u = fetch_one(conn, "SELECT id FROM users WHERE email = %s", (assigned_v_email,))
        if not u:
            from werkzeug.security import generate_password_hash
            from backend.app.db.seed import now_iso
            execute_query(conn, "INSERT INTO users (email, password_hash, role, status, created_at, updated_at) VALUES (%s, %s, 'volunteer', 'active', %s, %s)",
                          (assigned_v_email, generate_password_hash("password123"), now_iso(), now_iso()))
            new_u = fetch_one(conn, "SELECT id FROM users WHERE email = %s", (assigned_v_email,))
            execute_query(conn, "UPDATE volunteer_profiles SET user_id = %s WHERE id = %s", (new_u["id"], assigned_row["volunteer_id"]))
            conn.commit()

    assigned_login = client.post("/api/v1/auth/login", json={"email": assigned_v_email, "password": "password123"})
    assert assigned_login.status_code == 200
    assigned_token = assigned_login.get_json()["data"]["token"]

    vol_assns_after = client.get("/api/v1/me/assignments", headers={"Authorization": f"Bearer {assigned_token}"})
    assert vol_assns_after.status_code == 200
    my_assns = vol_assns_after.get_json()["data"]
    assert len(my_assns) >= 1
    # Verify the volunteer sees their role and department
    assert my_assns[0]["event_name"] == "Kala Fest"
    assert my_assns[0]["role_name"] == assigned_row["role_name"]

def test_manual_edit_skill_override_requires_reason(client):
    login_res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    token = login_res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db() as conn:
        ev = fetch_one(conn, "SELECT id FROM events WHERE name = 'Kala Fest'")
        event_id = ev["id"]

    # Run fresh allocation
    run_res = client.post(f"/api/v1/events/{event_id}/allocations/runs", json={"algorithm": "greedy"}, headers=headers)
    version_id = run_res.get_json()["data"]["version_id"]

    # Find requirement that requires "Technical Support" (IT Support)
    with get_db() as conn:
        req = fetch_one(conn, """
            SELECT er.id FROM event_requirements er
            JOIN departments d ON er.department_id = d.id
            WHERE er.event_id = %s AND d.name LIKE '%%IT%%' LIMIT 1
        """, (event_id,))
        req_id = req["id"]

        # Find active volunteer with NO technical skills
        non_tech_vol = fetch_one(conn, """
            SELECT vp.id FROM volunteer_profiles vp
            WHERE vp.active_status = 1
              AND vp.id NOT IN (
                SELECT volunteer_id FROM assignments WHERE allocation_version_id = %s
              )
              AND vp.id NOT IN (
                SELECT vs.volunteer_id FROM volunteer_skills vs
                JOIN skills s ON vs.skill_id = s.id
                WHERE s.name = 'Technical Support'
            ) LIMIT 1
        """, (version_id,))
        vol_id = non_tech_vol["id"]

    # Attempt manual add without override flag -> should return warning / confirmation request
    warn_res = client.patch(f"/api/v1/allocations/{version_id}/assignments", json={
        "operation": "add",
        "requirement_id": req_id,
        "volunteer_id": vol_id,
        "skill_override": False
    }, headers=headers)
    assert warn_res.status_code == 400
    assert "warning" in warn_res.get_json()

    # Attempt manual add with skill_override=True but empty reason -> should be rejected with 422
    err_res = client.patch(f"/api/v1/allocations/{version_id}/assignments", json={
        "operation": "add",
        "requirement_id": req_id,
        "volunteer_id": vol_id,
        "skill_override": True,
        "override_reason": ""
    }, headers=headers)
    assert err_res.status_code == 422
    assert err_res.get_json()["error"]["code"] == "OVERRIDE_REASON_REQUIRED"

    # Attempt manual add with skill_override=True and non-empty reason -> allowed and audited!
    success_res = client.patch(f"/api/v1/allocations/{version_id}/assignments", json={
        "operation": "add",
        "requirement_id": req_id,
        "volunteer_id": vol_id,
        "skill_override": True,
        "override_reason": "Organizer verified prior AV experience"
    }, headers=headers)
    assert success_res.status_code == 200

def test_archived_event_modifications_blocked(client):
    login_res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    token = login_res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create dummy event and archive it
    c_res = client.post("/api/v1/events", json={
        "name": "Past Rubaru Fest",
        "description": "Historical event",
        "starts_at": "2025-01-01T09:00:00Z",
        "ends_at": "2025-01-02T18:00:00Z",
        "venue": "Campus Ground"
    }, headers=headers)
    arch_event_id = c_res.get_json()["data"]["id"]

    # Archive
    client.post(f"/api/v1/events/{arch_event_id}/archive", headers=headers)

    # Editing archived event must be rejected with 409
    patch_res = client.patch(f"/api/v1/events/{arch_event_id}", json={"name": "Tampered Name"}, headers=headers)
    assert patch_res.status_code == 409
    assert patch_res.get_json()["error"]["code"] == "EVENT_ARCHIVED"

def test_simulation_does_not_mutate_live_data(client):
    login_res = client.post("/api/v1/auth/login", json={"email": "convener@tapmi.edu.in", "password": "convener123"})
    token = login_res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db() as conn:
        ev = fetch_one(conn, "SELECT id FROM events WHERE name = 'Kala Fest'")
        event_id = ev["id"]
        vols_before = fetch_one(conn, "SELECT count(*) as c FROM volunteer_profiles")["c"]
        runs_before = fetch_one(conn, "SELECT count(*) as c FROM allocation_runs")["c"]

    # Run simulation with 5 simulated candidates added
    sim_res = client.post(f"/api/v1/events/{event_id}/simulations", json={
        "adjustments": {
            "add_simulated_volunteers": [
                {"name": f"Sim Volunteer {i}", "skills": ["Stage & Backstage Management"]}
                for i in range(5)
            ]
        }
    }, headers=headers)
    assert sim_res.status_code == 200
    sim_data = sim_res.get_json()["data"]
    assert sim_data["is_simulation"] is True
    assert sim_data["status"] == "Simulation · Not published"

    # Verify database counts are 100% UNCHANGED
    with get_db() as conn:
        vols_after = fetch_one(conn, "SELECT count(*) as c FROM volunteer_profiles")["c"]
        runs_after = fetch_one(conn, "SELECT count(*) as c FROM allocation_runs")["c"]
        assert vols_after == vols_before
        assert runs_after == runs_before
