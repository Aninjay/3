from flask import Blueprint, request, jsonify, g
from backend.app.services.auth_service import (
    authenticate_user, request_activation_otp, verify_activation_otp,
    complete_activation, invalidate_session
)
from backend.app.auth_middleware import require_auth
from backend.app.db.connection import get_db, fetch_one

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    login_id = str(data.get("login_id") or data.get("email") or "").strip()
    password = data.get("password", "")

    if not login_id or not password:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Login ID and password are required."
            }
        }), 400

    result, err = authenticate_user(login_id, password)
    if err:
        return jsonify({
            "error": {
                "code": "AUTH_FAILED",
                "message": err
            }
        }), 401

    return jsonify({
        "data": {
            "token": result["token"],
            "user": result["user"]
        },
        "meta": {"message": "Login successful"}
    }), 200

@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.headers.get("X-Session-Token")
    if token:
        invalidate_session(token)
    return jsonify({"meta": {"message": "Logged out successfully"}}), 200

@auth_bp.route("/activation/request", methods=["POST"])
def activation_request():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    email = data.get("email", "").strip()

    if not student_id or not email:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Student ID and email are required."
            }
        }), 400

    ok, msg = request_activation_otp(student_id, email)
    return jsonify({"meta": {"message": msg}}), 200

@auth_bp.route("/activation/verify", methods=["POST"])
def activation_verify():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()

    if not student_id or not email or not otp:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Student ID, email, and OTP code are required."
            }
        }), 400

    ok, msg, ticket = verify_activation_otp(student_id, email, otp)
    if not ok:
        return jsonify({
            "error": {
                "code": "OTP_VERIFICATION_FAILED",
                "message": msg
            }
        }), 400

    return jsonify({
        "data": {"ticket": ticket},
        "meta": {"message": msg}
    }), 200

@auth_bp.route("/activation/complete", methods=["POST"])
def activation_complete():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not student_id or not email or not password:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Student ID, email, and password are required."
            }
        }), 400

    ok, msg = complete_activation(student_id, email, password)
    if not ok:
        return jsonify({
            "error": {
                "code": "ACTIVATION_FAILED",
                "message": msg
            }
        }), 400

    return jsonify({"meta": {"message": msg}}), 200
