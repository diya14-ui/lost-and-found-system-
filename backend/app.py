from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from py_backend.config import Config
from py_backend.db import test_connection
from py_backend.routes.auth_routes import auth_bp
from py_backend.routes.item_routes import item_bp
from py_backend.routes.claim_routes import claim_bp
from py_backend.routes.user_routes import user_bp
from py_backend.routes.contact_routes import contact_bp
import os


def create_app() -> Flask:
    app = Flask(__name__)
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    cors_origin = (Config.CORS_ORIGIN or "*").strip()

    if cors_origin == "*":
        CORS(app, resources={r"/api/.*": {"origins": "*"}})
    else:
        # Supports a single origin or comma-separated origins in .env
        origins = [origin.strip() for origin in cors_origin.split(",") if origin.strip()]
        CORS(app, resources={r"/api/.*": {"origins": origins}})

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "message": "API is running"})

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        return send_from_directory(uploads_dir, filename)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(item_bp, url_prefix="/api/items")
    app.register_blueprint(claim_bp, url_prefix="/api/claims")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")

    return app


app = create_app()

if __name__ == "__main__":
    try:
        test_connection()
        print("Database connection successful.")
    except Exception as error:
        # Keep API running so frontend gets a proper JSON error instead of connection refusal.
        print(f"Warning: Database is not reachable at startup: {error}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=False)
