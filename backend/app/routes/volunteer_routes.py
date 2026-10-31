from datetime import datetime, timezone
import re
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from backend.app.auth_middleware import require_auth, require_roles
from backend.app.services.auth_service import password_used_for_email
from backend.app.db.connection import transaction, get_db, fetch_one, fetch_all, execute_query
from backend.app.config import Config

volunteer_bp = Blueprint("volunteers", __name__)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@volunteer_bp.route("/volunteers", methods=["POST"])
@require_roles("convener", "co_convener")
def create_volunteer():
    data = request.get_json() or {}
    name = data.get("full_name", "").strip()
    student_id = data.get("student_id", "").strip().upper()
    email = Config.VOLUNTEER_LOGIN_EMAIL
    # `email` remains accepted as the original name of the contact-email field.
    contact_email = str(data.get("contact_email") or data.get("email") or "").strip().lower() or email
    password = data.get("password") or ""

    if not name or not student_id:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Full name and student ID are required."
            }
        }), 400
    if password and len(password) < 8:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "The password must contain at least 8 characters."}}), 400
    if contact_email != email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Enter a valid personal contact email."}}), 400

    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        # Check duplicate student ID
        existing_sid = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE UPPER(student_id) = %s", (student_id,))
        if existing_sid:
            return jsonify({
                "error": {
                    "code": "DUPLICATE_STUDENT_ID",
                    "message": f"A volunteer with student ID {student_id} already exists."
                }
            }), 409

        # The student ID is also the optional individual login alias.
        existing_login = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (student_id.lower(),))
        if existing_login:
            return jsonify({
                "error": {
                    "code": "DUPLICATE_LOGIN_ID",
                    "message": f"An account with student ID {student_id} already exists."
                }
            }), 409

        # A contact email that is already the login email of an individual
        # (non-shared) account belongs to that account and cannot be reused.
        if contact_email not in (Config.VOLUNTEER_LOGIN_EMAIL, Config.CORE_COMMITTEE_LOGIN_EMAIL):
            existing_email = fetch_one(conn, "SELECT id FROM users WHERE LOWER(email) = %s", (contact_email,))
            if existing_email:
                return jsonify({
                    "error": {
                        "code": "DUPLICATE_EMAIL",
                        "message": f"An account with email {contact_email} already exists."
                    }
                }), 409

        if password and password_used_for_email(conn, email, password):
            return jsonify({
                "error": {
                    "code": "DUPLICATE_SHARED_EMAIL_PASSWORD",
                    "message": "Choose a different password. Each account using this shared email needs its own password."
                }
            }), 409

        # With a password, create an active account with an individual
        # student-ID login. Without one, create a pending-activation account
        # that the volunteer activates through the OTP flow.
        account_status = 'active' if password else 'pending_activation'
        password_hash = generate_password_hash(password) if password else None
        execute_query(conn, """
            INSERT INTO users (email, login_id, password_hash, role, status, created_at, updated_at)
            VALUES (%s, %s, %s, 'volunteer', %s, %s, %s)
        """, (email, student_id, password_hash, account_status, ts, ts))
        user_row = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (student_id.lower(),))

        # Create volunteer profile
        execute_query(conn, """
            INSERT INTO volunteer_profiles (user_id, student_id, full_name, email, active_status, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 1, %s, %s, %s)
        """, (user_row["id"], student_id, name, contact_email, actor_id, ts, ts))
        vol_row = fetch_one(conn, "SELECT * FROM volunteer_profiles WHERE student_id = %s", (student_id,))

        # Audit
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, after_data, created_at)
            VALUES (%s, 'CREATE_VOLUNTEER', 'volunteer_profiles', %s, %s, %s)
        """, (actor_id, vol_row["id"], f"Created volunteer {student_id} ({name})", ts))

    success_message = (
        "Volunteer account created successfully. Sign in with the student ID and password."
        if password else
        "Volunteer created. The account activates when the volunteer completes OTP activation and sets a password."
    )
    return jsonify({
        "data": vol_row,
        "meta": {"message": success_message}
    }), 201

@volunteer_bp.route("/volunteers", methods=["GET"])
@require_roles("convener", "co_convener")
def list_volunteers():
    search = request.args.get("search", "").strip().lower()
    status_filter = request.args.get("status") # 'active', 'inactive', 'pending'

    query = """
        SELECT vp.*, u.status as account_status,
               (SELECT COUNT(*) FROM volunteer_skills vs WHERE vs.volunteer_id = vp.id) as skill_count
        FROM volunteer_profiles vp
        LEFT JOIN users u ON vp.user_id = u.id
        WHERE 1=1
    """
    params = []

    if search:
        query += """ AND (
            LOWER(vp.full_name) LIKE %s
            OR LOWER(vp.student_id) LIKE %s
            OR LOWER(vp.email) LIKE %s
            OR LOWER(COALESCE(vp.interviewed_by, '')) LIKE %s
            OR EXISTS (
                SELECT 1
                FROM volunteer_skills vs_search
                JOIN skills s_search ON s_search.id = vs_search.skill_id
                WHERE vs_search.volunteer_id = vp.id
                  AND LOWER(s_search.name) LIKE %s
            )
        )"""
        like_term = f"{search}%"
        params.extend([like_term, like_term, like_term, like_term, like_term])

    if status_filter == "active":
        query += " AND vp.active_status = 1"
    elif status_filter == "inactive":
        query += " AND vp.active_status = 0"
    elif status_filter == "pending":
        query += " AND (u.status = 'pending_activation' OR u.status IS NULL)"

    query += " ORDER BY vp.id ASC"

    with get_db() as conn:
        vols = fetch_all(conn, query, tuple(params))
        # Fetch skills for each volunteer
        for v in vols:
            skills = fetch_all(conn, """
                SELECT s.id, s.name FROM skills s
                JOIN volunteer_skills vs ON s.id = vs.skill_id
                WHERE vs.volunteer_id = %s
            """, (v["id"],))
            v["skills"] = skills

    return jsonify({
        "data": vols,
        "meta": {"count": len(vols)}
    }), 200

@volunteer_bp.route("/volunteers/<int:vol_id>", methods=["GET"])
@require_roles("convener", "co_convener")
def get_volunteer(vol_id):
    with get_db() as conn:
        v = fetch_one(conn, """
            SELECT vp.*, u.status as account_status
            FROM volunteer_profiles vp
            LEFT JOIN users u ON vp.user_id = u.id
            WHERE vp.id = %s
        """, (vol_id,))
        if not v:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Volunteer not found"}}), 404

        skills = fetch_all(conn, """
            SELECT s.id, s.name, s.description FROM skills s
            JOIN volunteer_skills vs ON s.id = vs.skill_id
            WHERE vs.volunteer_id = %s
        """, (vol_id,))
        v["skills"] = skills

        prefs = fetch_all(conn, """
            SELECT department_name, preference_rank FROM volunteer_preferences
            WHERE volunteer_id = %s ORDER BY preference_rank ASC
        """, (vol_id,))
        v["preferences"] = prefs

    return jsonify({"data": v}), 200

@volunteer_bp.route("/volunteers/<int:vol_id>", methods=["PATCH"])
@require_roles("convener", "co_convener")
def update_volunteer(vol_id):
    data = request.get_json() or {}
    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        existing = fetch_one(conn, "SELECT * FROM volunteer_profiles WHERE id = %s", (vol_id,))
        if not existing:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Volunteer not found"}}), 404

        if "active_status" in data:
            new_active = 1 if data["active_status"] else 0
            old_active = existing["active_status"]
            execute_query(conn, "UPDATE volunteer_profiles SET active_status = %s, updated_at = %s WHERE id = %s", (new_active, ts, vol_id))

            # Audit status change
            execute_query(conn, """
                INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, before_data, after_data, reason, created_at)
                VALUES (%s, 'VOLUNTEER_STATUS_CHANGE', 'volunteer_profiles', %s, %s, %s, %s, %s)
            """, (actor_id, vol_id, f"active_status: {old_active}", f"active_status: {new_active}", data.get("reason", "Organizer status update"), ts))

        if "full_name" in data:
            execute_query(conn, "UPDATE volunteer_profiles SET full_name = %s, updated_at = %s WHERE id = %s", (data["full_name"], ts, vol_id))

        updated = fetch_one(conn, "SELECT * FROM volunteer_profiles WHERE id = %s", (vol_id,))

    return jsonify({"data": updated, "meta": {"message": "Volunteer profile updated."}}), 200


@volunteer_bp.route("/volunteers/<int:vol_id>/password", methods=["PUT"])
@require_roles("convener", "co_convener")
def set_volunteer_password(vol_id):
    data = request.get_json() or {}
    password = data.get("password") or ""
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "The password must contain at least 8 characters."}}), 400

    ts = now_iso()
    actor_id = g.current_user["user_id"]
    with transaction() as conn:
        volunteer = fetch_one(conn, "SELECT * FROM volunteer_profiles WHERE id = %s", (vol_id,))
        if not volunteer:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Volunteer not found."}}), 404

        user = None
        if volunteer["user_id"]:
            user = fetch_one(conn, "SELECT id, role FROM users WHERE id = %s", (volunteer["user_id"],))
        if user and user["role"] != "volunteer":
            return jsonify({"error": {"code": "INVALID_ACCOUNT", "message": "This profile is not linked to a volunteer account."}}), 409

        if password_used_for_email(conn, Config.VOLUNTEER_LOGIN_EMAIL, password, user["id"] if user else None):
            return jsonify({
                "error": {
                    "code": "DUPLICATE_SHARED_EMAIL_PASSWORD",
                    "message": "Choose a different password. Each volunteer using the shared login email needs a unique password."
                }
            }), 409

        if user:
            execute_query(conn, """
                UPDATE users SET email = %s, login_id = %s, password_hash = %s, status = 'active', updated_at = %s
                WHERE id = %s
            """, (Config.VOLUNTEER_LOGIN_EMAIL, volunteer["student_id"], generate_password_hash(password), ts, user["id"]))
            action = "RESET_VOLUNTEER_PASSWORD"
        else:
            existing_login = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (volunteer["student_id"].lower(),))
            if existing_login:
                return jsonify({"error": {"code": "DUPLICATE_LOGIN_ID", "message": "This student ID is already linked to another login."}}), 409
            execute_query(conn, """
                INSERT INTO users (email, login_id, password_hash, role, status, created_at, updated_at)
                VALUES (%s, %s, %s, 'volunteer', 'active', %s, %s)
            """, (Config.VOLUNTEER_LOGIN_EMAIL, volunteer["student_id"], generate_password_hash(password), ts, ts))
            created_user = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (volunteer["student_id"].lower(),))
            user_id = created_user["id"]
            execute_query(conn, "UPDATE volunteer_profiles SET user_id = %s, updated_at = %s WHERE id = %s", (user_id, ts, vol_id))
            action = "SET_VOLUNTEER_PASSWORD"

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, after_data, reason, created_at)
            VALUES (%s, %s, 'volunteer_profiles', %s, %s, %s, %s)
        """, (actor_id, action, vol_id, "{\"password_updated\": true}", "Organizer set or reset volunteer password", ts))

    return jsonify({"meta": {"message": "Volunteer password saved securely. The existing password cannot be viewed; use reset to change it later."}}), 200

# Volunteer Self-Service endpoints
@volunteer_bp.route("/me", methods=["GET"])
@require_auth
def get_me():
    user = g.current_user
    with get_db() as conn:
        u_row = fetch_one(conn, "SELECT id, email, role, status, last_login_at FROM users WHERE id = %s", (user["user_id"],))
        vol_row = None
        if user["role"] == "volunteer" or user.get("volunteer_profile_id"):
            vol_row = fetch_one(conn, "SELECT id, student_id, full_name, email, active_status FROM volunteer_profiles WHERE user_id = %s", (user["user_id"],))

    return jsonify({
        "data": {
            "id": u_row["id"],
            "email": u_row["email"],
            "role": u_row["role"],
            "status": u_row["status"],
            "last_login_at": u_row["last_login_at"],
            "volunteer_profile": vol_row
        }
    }), 200

@volunteer_bp.route("/me/skills", methods=["GET"])
@require_auth
def get_my_skills():
    user = g.current_user
    with get_db() as conn:
        vol = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE user_id = %s", (user["user_id"],))
        if not vol:
            return jsonify({"data": []}), 200

        skills = fetch_all(conn, """
            SELECT s.id, s.name, s.description
            FROM skills s
            JOIN volunteer_skills vs ON s.id = vs.skill_id
            WHERE vs.volunteer_id = %s AND s.status = 'approved'
            ORDER BY s.name ASC
        """, (vol["id"],))

    return jsonify({"data": skills}), 200

@volunteer_bp.route("/me/skills", methods=["PUT"])
@require_auth
def update_my_skills():
    user = g.current_user
    data = request.get_json() or {}
    skill_ids = data.get("skill_ids", [])
    ts = now_iso()

    with transaction() as conn:
        vol = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE user_id = %s", (user["user_id"],))
        if not vol:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Volunteer profile not found."}}), 404

        vol_id = vol["id"]

        # Validate that all skill IDs are approved and exist
        if skill_ids:
            # Prevent duplicates
            unique_skill_ids = list(set(skill_ids))
            for s_id in unique_skill_ids:
                s_check = fetch_one(conn, "SELECT id FROM skills WHERE id = %s AND status = 'approved'", (s_id,))
                if not s_check:
                    return jsonify({
                        "error": {
                            "code": "INVALID_SKILL",
                            "message": f"Skill ID {s_id} is not an approved catalog skill."
                        }
                    }), 422

        # Replace volunteer skills
        execute_query(conn, "DELETE FROM volunteer_skills WHERE volunteer_id = %s", (vol_id,))
        for s_id in set(skill_ids):
            execute_query(conn, "INSERT INTO volunteer_skills (volunteer_id, skill_id, created_at) VALUES (%s, %s, %s)", (vol_id, s_id, ts))

        # Re-fetch updated skills
        skills = fetch_all(conn, """
            SELECT s.id, s.name, s.description
            FROM skills s
            JOIN volunteer_skills vs ON s.id = vs.skill_id
            WHERE vs.volunteer_id = %s
            ORDER BY s.name ASC
        """, (vol_id,))

    return jsonify({
        "data": skills,
        "meta": {"message": "Skills updated successfully."}
    }), 200

@volunteer_bp.route("/me/assignments", methods=["GET"])
@require_auth
def get_my_assignments():
    """
    Returns only the authenticated volunteer's published assignments for upcoming/ongoing events.
    Never exposes drafts or other volunteers' data.
    """
    user = g.current_user
    with get_db() as conn:
        vol = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE user_id = %s", (user["user_id"],))
        if not vol:
            return jsonify({"data": []}), 200

        assignments = fetch_all(conn, """
            SELECT a.id as assignment_id, a.assignment_source, a.created_at as assigned_at,
                   e.id as event_id, e.name as event_name, e.description as event_description,
                   e.starts_at, e.ends_at, e.venue, e.status as event_status,
                   d.name as department_name, er.role_name, er.priority
            FROM published_allocations pa
            JOIN assignments a ON pa.allocation_version_id = a.allocation_version_id
            JOIN event_requirements er ON a.requirement_id = er.id
            JOIN departments d ON er.department_id = d.id
            JOIN events e ON pa.event_id = e.id
            WHERE a.volunteer_id = %s AND e.status IN ('upcoming', 'ongoing')
            ORDER BY e.starts_at ASC
        """, (vol["id"],))

    return jsonify({"data": assignments}), 200

@volunteer_bp.route("/me/assignment-history", methods=["GET"])
@require_auth
def get_my_assignment_history():
    """
    Returns permitted historical assignments for completed events.
    """
    user = g.current_user
    with get_db() as conn:
        vol = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE user_id = %s", (user["user_id"],))
        if not vol:
            return jsonify({"data": []}), 200

        history = fetch_all(conn, """
            SELECT a.id as assignment_id, a.assignment_source,
                   e.id as event_id, e.name as event_name,
                   e.starts_at, e.ends_at, e.venue, e.status as event_status,
                   d.name as department_name, er.role_name
            FROM published_allocations pa
            JOIN assignments a ON pa.allocation_version_id = a.allocation_version_id
            JOIN event_requirements er ON a.requirement_id = er.id
            JOIN departments d ON er.department_id = d.id
            JOIN events e ON pa.event_id = e.id
            WHERE a.volunteer_id = %s AND e.status IN ('completed', 'archived')
            ORDER BY e.starts_at DESC
        """, (vol["id"],))

    return jsonify({"data": history}), 200
