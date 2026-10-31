from flask import Blueprint, jsonify
from backend.app.db.connection import get_db, fetch_one, is_postgres
from backend.app.config import Config

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    db_ok = False
    vol_count = 0
    event_count = 0

    try:
        with get_db() as conn:
            v_row = fetch_one(conn, "SELECT count(*) as c FROM volunteer_profiles")
            vol_count = v_row["c"] if v_row else 0
            e_row = fetch_one(conn, "SELECT count(*) as c FROM events")
            event_count = e_row["c"] if e_row else 0
            db_ok = True
    except Exception as e:
        db_ok = False

    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "database": {
            "connected": db_ok,
            "engine": "PostgreSQL" if is_postgres() else "SQLite (Local/Standalone)",
            "volunteer_profiles_count": vol_count,
            "events_count": event_count
        },
        "allocation_engine": {
            "greedy": "operational",
            "ilp_pulp": "operational"
        },
        "pilot_event": Config.PILOT_EVENT_NAME
    }), 200
