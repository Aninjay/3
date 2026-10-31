from functools import wraps
from flask import request, jsonify, g
from backend.app.services.auth_service import get_session

def get_current_user():
    # 1. Check Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    # 2. Check X-Session-Token header or cookie
    if not token:
        token = request.headers.get("X-Session-Token") or request.cookies.get("session_token")

    if not token:
        return None

    session_data = get_session(token)
    return session_data

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "error": {
                    "code": "UNAUTHENTICATED",
                    "message": "Authentication required. Please sign in."
                }
            }), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def require_roles(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({
                    "error": {
                        "code": "UNAUTHENTICATED",
                        "message": "Authentication required. Please sign in."
                    }
                }), 401
            if user["role"] not in allowed_roles:
                return jsonify({
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You do not have permission to perform this action."
                    }
                }), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator
