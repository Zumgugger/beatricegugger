"""Database models for the application."""
from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """Admin user model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class NavigationItem(db.Model):
    """Navigation menu items."""
    __tablename__ = 'navigation_items'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    icon_path = db.Column(db.String(255))  # Path to custom PNG
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<NavigationItem {self.title}>'


class Page(db.Model):
    """Static pages (About/Kontakt)."""
    __tablename__ = 'pages'
    
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Page {self.title}>'


class Course(db.Model):
    """Course offerings."""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    date = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    max_participants = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to registrations
    registrations = db.relationship('CourseRegistration', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def registration_count(self):
        """Get number of registrations for this course."""
        return self.registrations.count()
    
    @property
    def is_full(self):
        """Check if course is full."""
        if self.max_participants:
            return self.registration_count >= self.max_participants
        return False
    
    def __repr__(self):
        return f'<Course {self.title}>'


class CourseRegistration(db.Model):
    """Course registrations."""
    __tablename__ = 'course_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    vorname = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    telefonnummer = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))  # Optional, for confirmation email
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmation_sent = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<CourseRegistration {self.vorname} {self.name} for Course {self.course_id}>'


class ArtCategory(db.Model):
    """Art gallery categories."""
    __tablename__ = 'art_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    featured_image_path = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to images
    images = db.relationship('ArtImage', backref='category', lazy='dynamic', cascade='all, delete-orphan', order_by='ArtImage.order')
    
    def __repr__(self):
        return f'<ArtCategory {self.title}>'


class ArtImage(db.Model):
    """Images in art gallery."""
    __tablename__ = 'art_images'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('art_categories.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ArtImage {self.id} in Category {self.category_id}>'


class SiteSettings(db.Model):
    """Site-wide settings."""
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SiteSetting {self.key}>'
