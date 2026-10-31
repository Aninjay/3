import json
import re
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request
from werkzeug.security import generate_password_hash

from backend.app.auth_middleware import require_roles
from backend.app.services.auth_service import password_used_for_email
from backend.app.db.connection import execute_query, fetch_all, fetch_one, get_db, transaction
from backend.app.config import Config


core_committee_bp = Blueprint("core_committee", __name__)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


@core_committee_bp.route("/core-committee/members", methods=["GET"])
@require_roles("convener", "co_convener")
def list_core_committee_members():
    with get_db() as conn:
        members = fetch_all(conn, """
            SELECT u.id, u.email, u.login_id, u.status, ccp.full_name,
                   COUNT(dh.department_id) AS department_head_count
            FROM core_committee_profiles ccp
            JOIN users u ON u.id = ccp.user_id
            LEFT JOIN department_heads dh ON dh.user_id = u.id
            GROUP BY u.id, u.email, u.login_id, u.status, ccp.full_name
            ORDER BY LOWER(ccp.full_name), LOWER(u.email)
        """)

    return jsonify({"data": members}), 200


@core_committee_bp.route("/core-committee/members", methods=["POST"])
@require_roles("convener", "co_convener")
def create_core_committee_member():
    data = request.get_json() or {}
    full_name = str(data.get("full_name") or "").strip()
    email = Config.CORE_COMMITTEE_LOGIN_EMAIL
    contact_email = str(data.get("email") or "").strip().lower()
    login_id = str(data.get("login_id") or "").strip()
    if not login_id and contact_email:
        # Callers that predate the login-ID field identify the member by
        # their contact email; derive the login ID from its local part.
        login_id = contact_email.split("@")[0]
    password = data.get("password") or ""

    if not full_name or not email or not login_id or not password:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Full name, contact email, login ID, and password are required."
            }
        }), 400
    if (
        len(full_name) > 160
        or (contact_email and (len(contact_email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email)))
        or not re.fullmatch(r"[A-Za-z0-9._-]{2,80}", login_id)
    ):
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Enter a valid contact email, a login ID no longer than 80 characters, and a name no longer than 160 characters."
            }
        }), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The password must contain at least 8 characters."
            }
        }), 400

    ts = now_iso()
    actor_id = g.current_user["user_id"]
    with transaction() as conn:
        existing = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (login_id.lower(),))
        if existing:
            return jsonify({
                "error": {
                    "code": "DUPLICATE_LOGIN_ID",
                    "message": "That login ID is already in use. Choose a unique login ID."
                }
            }), 409

        if password_used_for_email(conn, email, password):
            return jsonify({
                "error": {
                    "code": "DUPLICATE_SHARED_EMAIL_PASSWORD",
                    "message": "Choose a different password. Each account using this shared email needs its own password."
                }
            }), 409

        execute_query(conn, """
            INSERT INTO users (email, login_id, password_hash, role, status, created_at, updated_at)
            VALUES (%s, %s, %s, 'core_committee', 'active', %s, %s)
        """, (email, login_id, generate_password_hash(password), ts, ts))
        user = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (login_id.lower(),))
        execute_query(conn, """
            INSERT INTO core_committee_profiles (user_id, full_name, email, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user["id"], full_name, contact_email or email, actor_id, ts, ts))
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, after_data, created_at)
            VALUES (%s, 'CREATE_CORE_COMMITTEE_MEMBER', 'core_committee_profiles', %s, %s, %s)
        """, (actor_id, user["id"], json.dumps({"full_name": full_name, "email": email, "login_id": login_id}), ts))

    return jsonify({
        "data": {
            "id": user["id"],
            "full_name": full_name,
            "email": email,
            "login_id": login_id,
            "role": "core_committee",
            "status": "active",
            "department_head_count": 0
        },
        "meta": {"message": "Core Committee account created successfully."}
    }), 201


@core_committee_bp.route("/core-committee/members/<int:user_id>/password", methods=["PUT"])
@require_roles("convener", "co_convener")
def set_core_committee_password(user_id):
    data = request.get_json() or {}
    password = data.get("password") or ""
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "The password must contain at least 8 characters."}}), 400

    ts = now_iso()
    actor_id = g.current_user["user_id"]
    with transaction() as conn:
        member = fetch_one(conn, """
            SELECT u.id, u.login_id, u.email
            FROM users u
            JOIN core_committee_profiles ccp ON ccp.user_id = u.id
            WHERE u.id = %s AND u.role = 'core_committee'
        """, (user_id,))
        if not member:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Core Committee member not found."}}), 404

        if password_used_for_email(conn, Config.CORE_COMMITTEE_LOGIN_EMAIL, password, user_id):
            return jsonify({
                "error": {
                    "code": "DUPLICATE_SHARED_EMAIL_PASSWORD",
                    "message": "Choose a different password. Each Core Committee member using the shared login email needs a unique password."
                }
            }), 409

        execute_query(conn, """
            UPDATE users SET email = %s, password_hash = %s, status = 'active', updated_at = %s
            WHERE id = %s
        """, (Config.CORE_COMMITTEE_LOGIN_EMAIL, generate_password_hash(password), ts, user_id))
        execute_query(conn, "UPDATE core_committee_profiles SET email = %s, updated_at = %s WHERE user_id = %s", (Config.CORE_COMMITTEE_LOGIN_EMAIL, ts, user_id))
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, after_data, reason, created_at)
            VALUES (%s, 'RESET_CORE_COMMITTEE_PASSWORD', 'core_committee_profiles', %s, %s, %s, %s)
        """, (actor_id, user_id, "{\"password_updated\": true}", "Organizer set or reset Core Committee password", ts))

    return jsonify({"meta": {"message": "Core Committee password saved securely. It cannot be viewed later; use reset to change it."}}), 200


@core_committee_bp.route("/events/<int:event_id>/department-heads", methods=["GET"])
@require_roles("convener", "co_convener")
def get_event_department_heads(event_id):
    with get_db() as conn:
        event = fetch_one(conn, """
            SELECT e.id, e.name, e.description, e.starts_at, e.ends_at, e.venue, e.status,
                   pa.allocation_version_id AS published_version_id
            FROM events e
            LEFT JOIN published_allocations pa ON pa.event_id = e.id
            WHERE e.id = %s
        """, (event_id,))
        if not event:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        departments = fetch_all(conn, """
            SELECT d.id AS department_id, d.name AS department_name,
                   COALESCE(SUM(er.headcount), 0) AS required_positions
            FROM event_requirements er
            JOIN departments d ON d.id = er.department_id
            WHERE er.event_id = %s
            GROUP BY d.id, d.name
            ORDER BY d.name
        """, (event_id,))

        if event["published_version_id"]:
            assigned_counts = fetch_all(conn, """
                SELECT er.department_id, COUNT(a.id) AS volunteer_count
                FROM assignments a
                JOIN event_requirements er ON er.id = a.requirement_id
                WHERE a.allocation_version_id = %s
                GROUP BY er.department_id
            """, (event["published_version_id"],))
        else:
            assigned_counts = []

        heads = fetch_all(conn, """
            SELECT dh.department_id, dh.user_id, ccp.full_name AS head_name, u.email AS head_email
            FROM department_heads dh
            JOIN core_committee_profiles ccp ON ccp.user_id = dh.user_id
            JOIN users u ON u.id = dh.user_id
            WHERE dh.event_id = %s
        """, (event_id,))

    count_by_department = {row["department_id"]: row["volunteer_count"] for row in assigned_counts}
    head_by_department = {row["department_id"]: row for row in heads}
    for department in departments:
        department["volunteer_count"] = count_by_department.get(department["department_id"], 0)
        head = head_by_department.get(department["department_id"])
        department["head_user_id"] = head["user_id"] if head else None
        department["head_name"] = head["head_name"] if head else None
        department["head_email"] = head["head_email"] if head else None

    return jsonify({"data": {"event": event, "departments": departments}}), 200


@core_committee_bp.route("/events/<int:event_id>/department-heads", methods=["PUT"])
@require_roles("convener", "co_convener")
def save_event_department_heads(event_id):
    data = request.get_json() or {}
    assignments = data.get("assignments")
    if not isinstance(assignments, list):
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Provide an assignments list covering each department for this event."
            }
        }), 400

    department_ids = []
    selected_user_ids = []
    try:
        for assignment in assignments:
            department_id = int(assignment["department_id"])
            department_ids.append(department_id)
            user_id = assignment.get("user_id")
            if user_id not in (None, ""):
                selected_user_ids.append(int(user_id))
    except (KeyError, TypeError, ValueError):
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Each department assignment must include valid department_id and user_id values."
            }
        }), 400

    if len(department_ids) != len(set(department_ids)):
        return jsonify({"error": {"code": "DUPLICATE_DEPARTMENT", "message": "A department can appear only once."}}), 422
    if len(selected_user_ids) != len(set(selected_user_ids)):
        return jsonify({
            "error": {
                "code": "CORE_MEMBER_ALREADY_ASSIGNED",
                "message": "A Core Committee member can head only one department per event. Choose a different member for each department."
            }
        }), 422

    ts = now_iso()
    actor_id = g.current_user["user_id"]
    with transaction() as conn:
        event = fetch_one(conn, "SELECT id, status FROM events WHERE id = %s", (event_id,))
        if not event:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404
        if event["status"] not in ("upcoming", "ongoing"):
            return jsonify({
                "error": {
                    "code": "EVENT_NOT_OPEN_FOR_HEAD_ASSIGNMENTS",
                    "message": "Department heads can be assigned while an event is upcoming or ongoing."
                }
            }), 409

        published = fetch_one(conn, "SELECT event_id FROM published_allocations WHERE event_id = %s", (event_id,))
        if not published:
            return jsonify({
                "error": {
                    "code": "PUBLISHED_ROSTER_REQUIRED",
                    "message": "Department heads can be assigned only after the event's allocation roster has been published."
                }
            }), 409

        event_departments = fetch_all(conn, """
            SELECT DISTINCT department_id FROM event_requirements WHERE event_id = %s
        """, (event_id,))
        valid_department_ids = {row["department_id"] for row in event_departments}
        if set(department_ids) != valid_department_ids:
            return jsonify({
                "error": {
                    "code": "DEPARTMENT_SET_MISMATCH",
                    "message": "Include each department in the event exactly once."
                }
            }), 422

        if selected_user_ids:
            valid_members = fetch_all(conn, """
                SELECT u.id FROM users u
                JOIN core_committee_profiles ccp ON ccp.user_id = u.id
                WHERE u.status = 'active' AND u.role = 'core_committee'
                  AND u.id IN (%s)
            """ % ",".join(["%s"] * len(selected_user_ids)), tuple(selected_user_ids))
            if {row["id"] for row in valid_members} != set(selected_user_ids):
                return jsonify({
                    "error": {
                        "code": "INVALID_CORE_COMMITTEE_MEMBER",
                        "message": "Choose active Core Committee accounts for department heads."
                    }
                }), 422

        before = fetch_all(conn, """
            SELECT department_id, user_id FROM department_heads WHERE event_id = %s ORDER BY department_id
        """, (event_id,))
        execute_query(conn, "DELETE FROM department_heads WHERE event_id = %s", (event_id,))
        for assignment in assignments:
            user_id = assignment.get("user_id")
            if user_id in (None, ""):
                continue
            execute_query(conn, """
                INSERT INTO department_heads (event_id, department_id, user_id, assigned_by, assigned_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (event_id, int(assignment["department_id"]), int(user_id), actor_id, ts))

        after = [
            {"department_id": int(row["department_id"]), "user_id": int(row["user_id"])}
            for row in assignments if row.get("user_id") not in (None, "")
        ]
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, before_data, after_data, created_at)
            VALUES (%s, 'UPDATE_DEPARTMENT_HEADS', 'events', %s, %s, %s, %s)
        """, (actor_id, event_id, json.dumps(before), json.dumps(after), ts))

    return jsonify({"meta": {"message": "Department heads saved successfully."}}), 200


@core_committee_bp.route("/me/department-assignments", methods=["GET"])
@require_roles("core_committee")
def get_my_department_assignments():
    user_id = g.current_user["user_id"]
    with get_db() as conn:
        rows = fetch_all(conn, """
            SELECT e.id AS event_id, e.name AS event_name, e.description AS event_description,
                   e.starts_at, e.ends_at, e.venue, e.status AS event_status,
                   COALESCE(av.status, 'not_started') AS allocation_status,
                   d.id AS department_id, d.name AS department_name,
                   a.id AS assignment_id, er.role_name,
                   vp.id AS volunteer_id, vp.full_name AS volunteer_name, vp.email AS volunteer_email
            FROM department_heads dh
            JOIN events e ON e.id = dh.event_id
            LEFT JOIN published_allocations pa ON pa.event_id = e.id
            LEFT JOIN allocation_versions av ON av.id = COALESCE(
                pa.allocation_version_id,
                (SELECT latest.id FROM allocation_versions latest
                 WHERE latest.event_id = e.id
                 ORDER BY latest.version_number DESC LIMIT 1)
            )
            JOIN departments d ON d.id = dh.department_id
            JOIN event_requirements er ON er.event_id = e.id AND er.department_id = d.id
            LEFT JOIN assignments a
                ON a.allocation_version_id = av.id
               AND a.requirement_id = er.id
            LEFT JOIN volunteer_profiles vp ON vp.id = a.volunteer_id
            WHERE dh.user_id = %s
            ORDER BY e.starts_at ASC, e.id ASC, d.name ASC, vp.full_name ASC
        """, (user_id,))

    events_by_id = {}
    departments_by_key = {}
    for row in rows:
        event = events_by_id.setdefault(row["event_id"], {
            "event_id": row["event_id"],
            "event_name": row["event_name"],
            "event_description": row["event_description"],
            "starts_at": row["starts_at"],
            "ends_at": row["ends_at"],
            "venue": row["venue"],
            "event_status": row["event_status"],
            "allocation_status": row["allocation_status"],
            "departments": []
        })
        department_key = (row["event_id"], row["department_id"])
        department = departments_by_key.get(department_key)
        if not department:
            department = {
                "department_id": row["department_id"],
                "department_name": row["department_name"],
                "volunteers": []
            }
            departments_by_key[department_key] = department
            event["departments"].append(department)

        if row["assignment_id"]:
            department["volunteers"].append({
                "id": row["volunteer_id"],
                "full_name": row["volunteer_name"],
                "email": row["volunteer_email"],
                "role_name": row["role_name"]
            })

    return jsonify({"data": list(events_by_id.values())}), 200
