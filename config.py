"""Application configuration."""
import os
from datetime import timedelta
from pathlib import Path

basedir = Path(__file__).parent.absolute()

# Explicitly set database path as string to avoid any path issues
DATABASE_PATH = str(basedir / "beatricegugger.db")


class Config:
    """Base configuration."""
    
    # Secret key for sessions
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database - ALWAYS use explicit absolute path (ignore DATABASE_URL from .env)
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    
    # File uploads
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    _upload_env = os.environ.get('UPLOAD_FOLDER')
    UPLOAD_FOLDER = Path(_upload_env) if _upload_env else basedir / 'uploads'
    _allowed_env = os.environ.get('ALLOWED_EXTENSIONS')
    ALLOWED_EXTENSIONS = {ext.strip().lower() for ext in _allowed_env.split(',')} if _allowed_env else {'png', 'jpg', 'jpeg', 'gif'}
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@beatricegugger.ch')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
    
    # Admin settings
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@beatricegugger.ch')
    
    # Twilio SMS settings
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')  # Your Twilio phone number
    SMS_ENABLED = os.environ.get('SMS_ENABLED', 'False').lower() == 'true'
    
    # Admin phone for notifications
    ADMIN_PHONE = os.environ.get('ADMIN_PHONE', '+41797134974')
    
    # Email reply-to (where replies should go)
    MAIL_REPLY_TO = os.environ.get('MAIL_REPLY_TO', 'info@beatricegugger.ch')
    
    # Pagination
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 10))
    
    # Flask port
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 5003))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    MAIL_DEBUG = True
    # Dev-friendly defaults - OK to have hardcoded fallbacks


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'https'
    
    # In production, SECRET_KEY must be set via environment
    # Note: Using class attribute, not @property (Flask can't handle property for SECRET_KEY)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CHANGE-THIS-IN-PRODUCTION'
    
    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY or self.SECRET_KEY == 'CHANGE-THIS-IN-PRODUCTION':
            raise ValueError("Production SECRET_KEY must be set via environment variable!")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
