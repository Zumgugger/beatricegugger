"""Flask application factory."""
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()


def create_app(config_name='development'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    
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
    
    return app


# Import models after db initialization to avoid circular imports
from app import models
