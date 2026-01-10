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


class WorkshopCategory(db.Model):
    """Workshop categories (sub-navigation on Angebot page)."""
    __tablename__ = 'workshop_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(255))  # Header image on detail page
    card_image_path = db.Column(db.String(255))  # Card image on overview page
    description = db.Column(db.Text)
    no_dates_text = db.Column(db.String(255), default='Neue Daten folgen')  # Text when no courses
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to courses
    courses = db.relationship('Course', backref='workshop_category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WorkshopCategory {self.title}>'


class Course(db.Model):
    """Course offerings."""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    workshop_category_id = db.Column(db.Integer, db.ForeignKey('workshop_categories.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    date = db.Column(db.DateTime)
    time_info = db.Column(db.String(100))  # e.g., "14:00 - 17:00"
    cost = db.Column(db.String(100))  # e.g., "CHF 120.-"
    location = db.Column(db.String(255))
    location_url = db.Column(db.String(500))  # Google Maps URL
    max_participants = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to registrations
    registrations = db.relationship('CourseRegistration', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def registration_count(self):
        """Get total number of participants for this course (excluding waitlist)."""
        from sqlalchemy import func
        result = db.session.query(func.sum(CourseRegistration.num_participants)).filter(
            CourseRegistration.course_id == self.id,
            CourseRegistration.is_waitlist == False
        ).scalar()
        return result or 0
    
    @property
    def spots_available(self):
        """Get number of available spots."""
        if self.max_participants:
            return max(0, self.max_participants - self.registration_count)
        return None  # Unlimited
    
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
    num_participants = db.Column(db.Integer, default=1)  # Number of people in this registration
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmation_sent = db.Column(db.Boolean, default=False)
    is_waitlist = db.Column(db.Boolean, default=False)  # True if on waitlist
    
    def __repr__(self):
        return f'<CourseRegistration {self.vorname} {self.name} ({self.num_participants}) for Course {self.course_id}>'


class ArtCategory(db.Model):
    """Art gallery categories."""
    __tablename__ = 'art_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True, default='')
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


class LocationMapping(db.Model):
    """Mapping of location addresses to Google Maps URLs."""
    __tablename__ = 'location_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), unique=True, nullable=False, index=True)
    google_maps_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<LocationMapping {self.address}>'


class SiteSettings(db.Model):
    """Site-wide settings."""
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SiteSetting {self.key}>'


class MessageTemplate(db.Model):
    """Email and SMS message templates."""
    __tablename__ = 'message_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Template identification
    message_type = db.Column(db.String(10), nullable=False)  # 'sms' or 'email'
    trigger = db.Column(db.String(50), nullable=False)  # e.g., 'registration_confirmed', 'registration_waitlist', 'reminder_1day', 'promoted_from_waitlist'
    
    # Template content
    subject = db.Column(db.String(255))  # For emails only
    body = db.Column(db.Text, nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one template per type+trigger combination
    __table_args__ = (db.UniqueConstraint('message_type', 'trigger', name='uq_message_template'),)
    
    def __repr__(self):
        return f'<MessageTemplate {self.message_type}:{self.trigger}>'
    
    def render(self, **context):
        """Render template with context variables.
        
        Available variables:
        - {vorname}, {name}, {telefonnummer}, {email}
        - {kurstitel}, {datum}, {zeit}, {ort}, {ort_url}
        - {num_registered}, {num_waitlist}
        """
        text = self.body
        for key, value in context.items():
            text = text.replace('{' + key + '}', str(value) if value else '')
        return text
    
    def render_subject(self, **context):
        """Render email subject with context variables."""
        if not self.subject:
            return ''
        text = self.subject
        for key, value in context.items():
            text = text.replace('{' + key + '}', str(value) if value else '')
        return text


class MessageLog(db.Model):
    """Log of sent messages for tracking and debugging."""
    __tablename__ = 'message_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Message details
    message_type = db.Column(db.String(10), nullable=False)  # 'sms' or 'email'
    trigger = db.Column(db.String(50), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)  # Phone or email
    subject = db.Column(db.String(255))  # For emails
    body = db.Column(db.Text, nullable=False)
    
    # Related entities
    registration_id = db.Column(db.Integer, db.ForeignKey('course_registrations.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='sent')  # sent, failed, pending
    error_message = db.Column(db.Text)
    external_id = db.Column(db.String(100))  # Twilio SID or email message ID
    
    # Timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    registration = db.relationship('CourseRegistration', backref='messages')
    course = db.relationship('Course', backref='messages')
    
    def __repr__(self):
        return f'<MessageLog {self.message_type} to {self.recipient}>'


class ScheduledMessage(db.Model):
    """Scheduled messages (e.g., SMS reminders)."""
    __tablename__ = 'scheduled_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Message details
    message_type = db.Column(db.String(10), nullable=False)  # 'sms' or 'email'
    trigger = db.Column(db.String(50), nullable=False)  # e.g., 'reminder_1day'
    recipient = db.Column(db.String(255), nullable=False)
    
    # Related entities
    registration_id = db.Column(db.Integer, db.ForeignKey('course_registrations.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    
    # Scheduling
    scheduled_for = db.Column(db.DateTime, nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, sent, cancelled, failed
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    registration = db.relationship('CourseRegistration', backref='scheduled_messages')
    course = db.relationship('Course', backref='scheduled_messages')
    
    def __repr__(self):
        return f'<ScheduledMessage {self.trigger} for {self.scheduled_for}>'

