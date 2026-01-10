"""Flask application factory."""
import logging
from flask import Flask, send_from_directory, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def create_app(config_name='development'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'admin.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes import public, admin, courses, art
    app.register_blueprint(public.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(courses.bp)
    app.register_blueprint(art.bp)
    
    # Create upload directories
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'] / 'courses', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'] / 'art', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'] / 'pages', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'] / 'navigation', exist_ok=True)

    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        import os
        from pathlib import Path
        upload_folder = app.config['UPLOAD_FOLDER']
        # Ensure we use absolute path
        if not Path(upload_folder).is_absolute():
            upload_folder = Path(app.root_path).parent / upload_folder
        return send_from_directory(str(upload_folder), filename)
    
    # Health check endpoint for production monitoring
    @app.route('/health')
    def health_check():
        try:
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            return jsonify({'status': 'healthy', 'database': 'connected'}), 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {error}")
        return render_template('errors/500.html'), 500
    
    return app


# Import models after db initialization to avoid circular imports
from app import models
