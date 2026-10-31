import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from backend.app.config import Config

def create_app(config_class=Config):
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    
    app = Flask(
        __name__,
        static_folder=str(frontend_dist) if frontend_dist.exists() else None,
        static_url_path="/"
    )
    app.config.from_object(config_class)

    # The API uses bearer tokens, so cookies are unnecessary. Restrict origins
    # in deployment with CORS_ORIGINS; wildcard remains convenient for local dev.
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Register blueprints under /api/v1
    from backend.app.routes.health import health_bp
    from backend.app.routes.auth_routes import auth_bp
    from backend.app.routes.volunteer_routes import volunteer_bp
    from backend.app.routes.skill_routes import skill_bp
    from backend.app.routes.event_routes import event_bp
    from backend.app.routes.allocation_routes import allocation_bp
    from backend.app.routes.report_routes import report_bp
    from backend.app.routes.simulation_routes import simulation_bp
    from backend.app.routes.core_committee_routes import core_committee_bp

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(volunteer_bp, url_prefix="/api/v1")
    app.register_blueprint(skill_bp, url_prefix="/api/v1")
    app.register_blueprint(event_bp, url_prefix="/api/v1")
    app.register_blueprint(allocation_bp, url_prefix="/api/v1")
    app.register_blueprint(report_bp, url_prefix="/api/v1")
    app.register_blueprint(simulation_bp, url_prefix="/api/v1")
    app.register_blueprint(core_committee_bp, url_prefix="/api/v1")

    # Serve React SPA when frontend/dist is present
    if frontend_dist.exists():
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path):
            if path != "" and (frontend_dist / path).exists():
                return send_from_directory(str(frontend_dist), path)
            return send_from_directory(str(frontend_dist), "index.html")

    # Standard error handlers conforming to API_SPEC.md
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "error": {
                "code": "BAD_REQUEST",
                "message": getattr(e, "description", "Malformed request.")
            }
        }), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": getattr(e, "description", "Requested resource was not found.")
            }
        }), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server."
            }
        }), 500

    return app
