from flask import Blueprint, request, jsonify
from backend.app.auth_middleware import require_roles
from backend.app.db.connection import get_db
from backend.app.allocation.simulator import run_simulation
from backend.app.routes.allocation_routes import load_snapshot_data

simulation_bp = Blueprint("simulations", __name__)

@simulation_bp.route("/events/<int:event_id>/simulations", methods=["POST"])
@require_roles("convener", "co_convener")
def create_simulation(event_id):
    data = request.get_json() or {}
    adjustments = data.get("adjustments", {})
    algorithm = data.get("algorithm", "ilp").lower()

    with get_db() as conn:
        vols, reqs, fingerprint = load_snapshot_data(conn, event_id)
        if not reqs:
            return jsonify({"error": {"code": "NO_DATA", "message": "No event requirements available for simulation."}}), 400

        sim_result = run_simulation(vols, reqs, adjustments, algorithm=algorithm)

    return jsonify({"data": sim_result}), 200
