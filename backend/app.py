from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from py_backend.config import Config
from py_backend.db import test_connection
from py_backend.routes.auth_routes import auth_bp
from py_backend.routes.item_routes import item_bp
from py_backend.routes.claim_routes import claim_bp
from py_backend.routes.user_routes import user_bp
from py_backend.routes.contact_routes import contact_bp
from py_backend.routes.admin_routes import admin_bp
from py_backend.utils.schema import ensure_admin_columns
from py_backend.middleware.csrf import register_csrf
import os


def create_app() -> Flask:
    app = Flask(__name__)
    backend_dir = os.path.dirname(__file__)
    workspace_dir = os.path.abspath(os.path.join(backend_dir, ".."))
    frontend_dir = os.path.join(workspace_dir, "frontend")
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Enable CORS for API routes. Use a permissive policy in development
    # so pages served by Live Server (different origin) can access the API.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "message": "API is running"})

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        return send_from_directory(uploads_dir, filename)

    @app.get("/")
    def root_page():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/frontend/<path:filename>")
    def frontend_files(filename: str):
        return send_from_directory(frontend_dir, filename)

    @app.get("/css/<path:filename>")
    def frontend_css_files(filename: str):
        return send_from_directory(os.path.join(frontend_dir, "css"), filename)

    @app.get("/js/<path:filename>")
    def frontend_js_files(filename: str):
        return send_from_directory(os.path.join(frontend_dir, "js"), filename)

    @app.get("/images/<path:filename>")
    def frontend_image_files(filename: str):
        return send_from_directory(os.path.join(frontend_dir, "images"), filename)

    @app.get("/<path:filename>")
    def frontend_html_files(filename: str):
        if filename.endswith(".html"):
            return send_from_directory(frontend_dir, filename)
        return jsonify({"success": False, "message": "Not found"}), 404

    @app.get("/admin/login")
    def admin_login_page():
        return send_from_directory(frontend_dir, "admin-login.html")

    @app.get("/admin/dashboard")
    def admin_dashboard_page():
        return send_from_directory(frontend_dir, "admin-dashboard.html")

    @app.get("/admin/index.html")
    def admin_index_page():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/admin/css/<path:filename>")
    def admin_css_files(filename: str):
        return send_from_directory(os.path.join(frontend_dir, "css"), filename)

    @app.get("/admin/js/<path:filename>")
    def admin_js_files(filename: str):
        return send_from_directory(os.path.join(frontend_dir, "js"), filename)

    @app.get("/admin/images/<path:filename>")
    def admin_image_files(filename: str):
        return send_from_directory(os.path.join(frontend_dir, "images"), filename)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(item_bp, url_prefix="/api/items")
    app.register_blueprint(claim_bp, url_prefix="/api/claims")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # Register CSRF middleware (lightweight, opt-in behavior)
    try:
        register_csrf(app)
    except Exception:
        pass

    return app


app = create_app()

if __name__ == "__main__":
    try:
        test_connection()
        ensure_admin_columns()
        print("Database connection successful.")
    except Exception as error:
        # Keep API running so frontend gets a proper JSON error instead of connection refusal.
        print(f"Warning: Database is not reachable at startup: {error}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=False)
