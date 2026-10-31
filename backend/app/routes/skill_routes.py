from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from backend.app.auth_middleware import require_auth, require_roles
from backend.app.db.connection import transaction, get_db, fetch_one, fetch_all, execute_query

skill_bp = Blueprint("skills", __name__)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

@skill_bp.route("/skills", methods=["GET"])
def list_skills():
    """
    Returns approved skills available in catalog.
    """
    with get_db() as conn:
        skills = fetch_all(conn, """
            SELECT id, name, description, status
            FROM skills
            WHERE status = 'approved'
            ORDER BY name ASC
        """)
    return jsonify({"data": skills}), 200

@skill_bp.route("/skills/suggestions", methods=["POST"])
@require_auth
def suggest_skill():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()

    if not name:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Skill name is required."}}), 400

    ts = now_iso()
    user_id = g.current_user["user_id"]

    with transaction() as conn:
        existing = fetch_one(conn, "SELECT id, status FROM skills WHERE LOWER(name) = %s", (name.lower(),))
        if existing:
            return jsonify({
                "error": {
                    "code": "DUPLICATE_SKILL",
                    "message": f"Skill '{name}' already exists with status: {existing['status']}."
                }
            }), 409

        execute_query(conn, """
            INSERT INTO skills (name, description, status, created_by, created_at)
            VALUES (%s, %s, 'pending', %s, %s)
        """, (name, desc, user_id, ts))
        new_skill = fetch_one(conn, "SELECT * FROM skills WHERE LOWER(name) = %s", (name.lower(),))

    return jsonify({
        "data": new_skill,
        "meta": {"message": "Skill suggestion submitted for organizer review."}
    }), 201

@skill_bp.route("/skills/suggestions", methods=["GET"])
@require_roles("convener", "co_convener")
def list_suggestions():
    with get_db() as conn:
        suggestions = fetch_all(conn, """
            SELECT s.*, u.email as suggested_by_email
            FROM skills s
            LEFT JOIN users u ON s.created_by = u.id
            WHERE s.status = 'pending'
            ORDER BY s.id DESC
        """)
    return jsonify({"data": suggestions}), 200

@skill_bp.route("/skills/suggestions/<int:skill_id>/approve", methods=["POST"])
@require_roles("convener", "co_convener")
def approve_suggestion(skill_id):
    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        s = fetch_one(conn, "SELECT * FROM skills WHERE id = %s", (skill_id,))
        if not s:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Skill not found."}}), 404

        execute_query(conn, """
            UPDATE skills
            SET status = 'approved', approved_by = %s, approved_at = %s
            WHERE id = %s
        """, (actor_id, ts, skill_id))

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'SKILL_APPROVED', 'skills', %s, %s, %s)
        """, (actor_id, skill_id, f"Approved skill '{s['name']}'", ts))

    return jsonify({"meta": {"message": f"Skill '{s['name']}' approved into catalog."}}), 200

@skill_bp.route("/skills/suggestions/<int:skill_id>/reject", methods=["POST"])
@require_roles("convener", "co_convener")
def reject_suggestion(skill_id):
    data = request.get_json() or {}
    reason = data.get("reason", "Rejected by organizer")
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        s = fetch_one(conn, "SELECT * FROM skills WHERE id = %s", (skill_id,))
        if not s:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Skill not found."}}), 404

        execute_query(conn, "UPDATE skills SET status = 'rejected' WHERE id = %s", (skill_id,))

        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'SKILL_REJECTED', 'skills', %s, %s, %s)
        """, (actor_id, skill_id, reason, now_iso()))

    return jsonify({"meta": {"message": f"Skill suggestion '{s['name']}' rejected."}}), 200
