import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from models import db
from routes.auth import auth_bp
from routes.reviews import reviews_bp
from routes.dashboard import dashboard_bp


def create_app(config_class=Config):
    """Application factory for Flask API."""
    backend_dir = Path(__file__).resolve().parent
    frontend_dir = backend_dir.parent / 'frontend'

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path=''
    )
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing (CORS)
    # Allows deployed frontend on Vercel/Render or local dev to talk to backend
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize database
    db.init_app(app)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(dashboard_bp)

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        db_status = "connected"
        try:
            db.session.execute(db.text('SELECT 1'))
        except Exception:
            db_status = "disconnected"

        return jsonify({
            'status': 'healthy',
            'service': 'AI Code Review API',
            'database': db_status,
            'gemini_configured': bool(app.config.get('GEMINI_API_KEY'))
        }), 200

    # Serve frontend static files when accessed directly via Flask
    @app.route('/', methods=['GET'])
    def serve_index():
        if frontend_dir.exists():
            return send_from_directory(str(frontend_dir), 'index.html')
        return jsonify({'message': 'AI Code Review API is running. Access /api/health.'})

    @app.route('/<path:path>', methods=['GET'])
    def serve_frontend_file(path):
        target_file = frontend_dir / path
        if frontend_dir.exists() and target_file.exists():
            return send_from_directory(str(frontend_dir), path)
        return jsonify({'error': 'Resource not found', 'path': path}), 404

    # Global Error Handlers (never expose internal tracebacks to users)
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({'success': False, 'error': 'Requested endpoint or resource was not found.'}), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        return jsonify({'success': False, 'error': 'An internal server error occurred. Please try again later.'}), 500

    # Ensure tables exist on startup
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"[*] Starting AI Code Review API on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
