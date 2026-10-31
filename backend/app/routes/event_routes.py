from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from backend.app.auth_middleware import require_auth, require_roles
from backend.app.db.connection import transaction, get_db, fetch_one, fetch_all, execute_query
from backend.app.allocation.capacity import calculate_workload_capacity

event_bp = Blueprint("events", __name__)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@event_bp.route("/events", methods=["GET"])
@require_auth
def list_events():
    user = g.current_user
    is_organizer = user["role"] in ("convener", "co_convener")

    query = """
        SELECT e.*,
               u.email as creator_email,
               pa.allocation_version_id as published_version_id,
               (SELECT COUNT(*) FROM event_requirements er WHERE er.event_id = e.id) as requirement_count,
               (SELECT COALESCE(SUM(headcount), 0) FROM event_requirements er WHERE er.event_id = e.id) as total_required
        FROM events e
        LEFT JOIN users u ON e.created_by = u.id
        LEFT JOIN published_allocations pa ON e.id = pa.event_id
    """
    if not is_organizer:
        query += " WHERE e.status IN ('upcoming', 'ongoing', 'completed')"

    query += " ORDER BY CASE e.status WHEN 'upcoming' THEN 1 WHEN 'ongoing' THEN 2 WHEN 'draft' THEN 3 WHEN 'completed' THEN 4 ELSE 5 END, e.starts_at ASC"

    with get_db() as conn:
        events = fetch_all(conn, query)
        for ev in events:
            # If published version exists, calculate published allocated count
            if ev["published_version_id"]:
                alloc_row = fetch_one(conn, """
                    SELECT COUNT(*) as c FROM assignments
                    WHERE allocation_version_id = %s
                """, (ev["published_version_id"],))
                ev["total_allocated"] = alloc_row["c"]
                ev["total_vacancies"] = max(0, ev["total_required"] - alloc_row["c"])
            else:
                ev["total_allocated"] = 0
                ev["total_vacancies"] = ev["total_required"]

    return jsonify({"data": events}), 200

@event_bp.route("/events", methods=["POST"])
@require_roles("convener", "co_convener")
def create_event():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    starts_at = data.get("starts_at", "").strip()
    ends_at = data.get("ends_at", "").strip()
    venue = data.get("venue", "").strip()

    if not name or not starts_at or not ends_at or not venue:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Event name, starts_at, ends_at, and venue are required."
            }
        }), 400

    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        execute_query(conn, """
            INSERT INTO events (name, description, starts_at, ends_at, venue, status, created_by, updated_by, created_at, updated_at, version)
            VALUES (%s, %s, %s, %s, %s, 'upcoming', %s, %s, %s, %s, 1)
        """, (name, desc, starts_at, ends_at, venue, actor_id, actor_id, ts, ts))
        new_event = fetch_one(conn, "SELECT * FROM events WHERE name = %s ORDER BY id DESC LIMIT 1", (name,))

        # Initialize default availability for all active volunteers for this event
        active_vols = fetch_all(conn, "SELECT id FROM volunteer_profiles WHERE active_status = 1")
        for v in active_vols:
            execute_query(conn, """
                INSERT INTO volunteer_availability (volunteer_id, event_id, available, availability_start, availability_end, max_hours)
                VALUES (%s, %s, 1, '09:00', '21:00', 8.0)
            """, (v["id"], new_event["id"]))

        # Audit
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, after_data, created_at)
            VALUES (%s, 'CREATE_EVENT', 'events', %s, %s, %s)
        """, (actor_id, new_event["id"], f"Created event '{name}'", ts))

    return jsonify({"data": new_event}), 201

@event_bp.route("/events/<int:event_id>", methods=["GET"])
@require_auth
def get_event(event_id):
    with get_db() as conn:
        ev = fetch_one(conn, """
            SELECT e.*, pa.allocation_version_id as published_version_id
            FROM events e
            LEFT JOIN published_allocations pa ON e.id = pa.event_id
            WHERE e.id = %s
        """, (event_id,))
        if not ev:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        # Requirements
        reqs = fetch_all(conn, """
            SELECT er.*, d.name as department_name
            FROM event_requirements er
            JOIN departments d ON er.department_id = d.id
            WHERE er.event_id = %s
            ORDER BY CASE er.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END, er.id ASC
        """, (event_id,))

        for r in reqs:
            sk_rows = fetch_all(conn, """
                SELECT s.id, s.name, rs.is_mandatory, rs.is_preferred
                FROM requirement_skills rs
                JOIN skills s ON rs.skill_id = s.id
                WHERE rs.requirement_id = %s
            """, (r["id"],))
            r["skills"] = sk_rows
            r["mandatory_skills"] = [s["name"] for s in sk_rows if s["is_mandatory"]]
            r["preferred_skills"] = [s["name"] for s in sk_rows if s["is_preferred"]]

        ev["requirements"] = reqs

    return jsonify({"data": ev}), 200

@event_bp.route("/events/<int:event_id>", methods=["PATCH"])
@require_roles("convener", "co_convener")
def update_event(event_id):
    data = request.get_json() or {}
    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        ev = fetch_one(conn, "SELECT * FROM events WHERE id = %s", (event_id,))
        if not ev:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        if ev["status"] == "archived":
            return jsonify({
                "error": {
                    "code": "EVENT_ARCHIVED",
                    "message": "Archived events are read-only and cannot be modified."
                }
            }), 409

        name = data.get("name", ev["name"])
        desc = data.get("description", ev["description"])
        starts_at = data.get("starts_at", ev["starts_at"])
        ends_at = data.get("ends_at", ev["ends_at"])
        venue = data.get("venue", ev["venue"])
        status = data.get("status", ev["status"])

        execute_query(conn, """
            UPDATE events
            SET name = %s, description = %s, starts_at = %s, ends_at = %s, venue = %s, status = %s, updated_by = %s, updated_at = %s, version = version + 1
            WHERE id = %s
        """, (name, desc, starts_at, ends_at, venue, status, actor_id, ts, event_id))

        updated = fetch_one(conn, "SELECT * FROM events WHERE id = %s", (event_id,))

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'UPDATE_EVENT', 'events', %s, 'Updated event details', %s)
        """, (actor_id, event_id, ts))

    return jsonify({"data": updated}), 200

@event_bp.route("/events/<int:event_id>/cancel", methods=["POST"])
@require_roles("convener", "co_convener")
def cancel_event(event_id):
    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        ev = fetch_one(conn, "SELECT * FROM events WHERE id = %s", (event_id,))
        if not ev:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        execute_query(conn, "UPDATE events SET status = 'cancelled', updated_at = %s WHERE id = %s", (ts, event_id))

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'CANCEL_EVENT', 'events', %s, 'Organizer marked event cancelled', %s)
        """, (actor_id, event_id, ts))

    return jsonify({"meta": {"message": f"Event '{ev['name']}' has been cancelled."}}), 200

@event_bp.route("/events/<int:event_id>/archive", methods=["POST"])
@require_roles("convener", "co_convener")
def archive_event(event_id):
    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        ev = fetch_one(conn, "SELECT * FROM events WHERE id = %s", (event_id,))
        if not ev:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        execute_query(conn, "UPDATE events SET status = 'archived', updated_at = %s WHERE id = %s", (ts, event_id))

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'ARCHIVE_EVENT', 'events', %s, 'Organizer archived completed event', %s)
        """, (actor_id, event_id, ts))

    return jsonify({"meta": {"message": f"Event '{ev['name']}' is now archived and read-only."}}), 200

@event_bp.route("/events/<int:event_id>/requirements", methods=["GET"])
@require_roles("convener", "co_convener")
def get_event_requirements(event_id):
    with get_db() as conn:
        reqs = fetch_all(conn, """
            SELECT er.*, d.name as department_name
            FROM event_requirements er
            JOIN departments d ON er.department_id = d.id
            WHERE er.event_id = %s
            ORDER BY CASE er.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END, er.id ASC
        """, (event_id,))

        for r in reqs:
            sk = fetch_all(conn, """
                SELECT s.id, s.name, rs.is_mandatory, rs.is_preferred
                FROM requirement_skills rs
                JOIN skills s ON rs.skill_id = s.id
                WHERE rs.requirement_id = %s
            """, (r["id"],))
            r["skills"] = sk
            r["mandatory_skills"] = [s["name"] for s in sk if s["is_mandatory"]]
            r["preferred_skills"] = [s["name"] for s in sk if s["is_preferred"]]

    return jsonify({"data": reqs}), 200

@event_bp.route("/events/<int:event_id>/requirements", methods=["PUT"])
@require_roles("convener", "co_convener")
def update_event_requirements(event_id):
    data = request.get_json() or {}
    req_items = data.get("requirements", [])
    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        ev = fetch_one(conn, "SELECT * FROM events WHERE id = %s", (event_id,))
        if not ev:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404
        if ev["status"] == "archived":
            return jsonify({"error": {"code": "EVENT_ARCHIVED", "message": "Archived events cannot be edited."}}), 409

        # Delete existing requirement skills & requirements
        execute_query(conn, """
            DELETE FROM requirement_skills
            WHERE requirement_id IN (SELECT id FROM event_requirements WHERE event_id = %s)
        """, (event_id,))
        execute_query(conn, "DELETE FROM event_requirements WHERE event_id = %s", (event_id,))

        for item in req_items:
            dept_id = item.get("department_id")
            role_name = item.get("role_name", "").strip()
            headcount = int(item.get("headcount", 1))
            priority = item.get("priority", "normal").lower()
            source = item.get("requirement_source", "fixed_headcount")
            duration = float(item.get("duration_hours", 8.0))

            if headcount < 0:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Headcount cannot be negative."}}), 400

            execute_query(conn, """
                INSERT INTO event_requirements (
                    event_id, department_id, role_name, headcount, priority, duration_hours,
                    workload_value, workload_unit, service_time_value, service_time_unit,
                    peak_window_value, peak_window_unit, requirement_source, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_id, dept_id, role_name, headcount, priority, duration,
                item.get("workload_value"), item.get("workload_unit"),
                item.get("service_time_value"), item.get("service_time_unit"),
                item.get("peak_window_value"), item.get("peak_window_unit"),
                source, ts, ts
            ))
            new_r = fetch_one(conn, "SELECT id FROM event_requirements WHERE event_id = %s ORDER BY id DESC LIMIT 1", (event_id,))
            new_r_id = new_r["id"]

            # Mandatory skills
            for s_id in item.get("mandatory_skill_ids", []):
                execute_query(conn, "INSERT INTO requirement_skills (requirement_id, skill_id, is_mandatory, is_preferred) VALUES (%s, %s, 1, 0)", (new_r_id, s_id))

            # Preferred skills
            for s_id in item.get("preferred_skill_ids", []):
                if s_id not in item.get("mandatory_skill_ids", []):
                    execute_query(conn, "INSERT INTO requirement_skills (requirement_id, skill_id, is_mandatory, is_preferred) VALUES (%s, %s, 0, 1)", (new_r_id, s_id))

        # Invalidate any pending approved allocation for this event
        execute_query(conn, """
            UPDATE allocation_versions
            SET status = 'draft', change_summary = 'Approval invalidated due to requirements update'
            WHERE event_id = %s AND status = 'approved'
        """, (event_id,))

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'UPDATE_REQUIREMENTS', 'events', %s, 'Updated event staffing requirements', %s)
        """, (actor_id, event_id, ts))

    return jsonify({"meta": {"message": "Event requirements updated successfully."}}), 200

@event_bp.route("/events/<int:event_id>/requirements/calculate", methods=["POST"])
@require_roles("convener", "co_convener")
def calculate_capacity(event_id):
    data = request.get_json() or {}
    try:
        workload = float(data.get("workload_value", 0))
        service_time = float(data.get("service_time_value", 0))
        peak_window = float(data.get("peak_window_value", 0))

        result = calculate_workload_capacity(workload, service_time, peak_window)
        return jsonify({"data": result}), 200
    except ValueError as ve:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": str(ve)}}), 400
