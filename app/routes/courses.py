"""Course routes (listing, detail, registration)."""
import logging
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user
from app import db, mail, limiter
from app.models import Course, CourseRegistration, NavigationItem, WorkshopCategory, Page
from flask_mail import Message
import os

logger = logging.getLogger(__name__)

bp = Blueprint('courses', __name__, url_prefix='/angebot')


def validate_phone(phone: str) -> bool:
    """Validate phone number - flexible format.
    
    Accepts: +41 79 123 45 67, 079 123 45 67, 0791234567, +41(0)79 123 45 67, etc.
    """
    if not phone:
        return False
    # Remove all formatting characters
    cleaned = re.sub(r'[\s\-\.\(\)]+', '', phone)
    # Should be digits, optionally starting with +
    if not re.match(r'^\+?\d{9,15}$', cleaned):
        return False
    return True


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return True  # Email is optional
    # Basic pattern: something@something.something
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


@bp.route('/')
def index():
    """List all workshop categories."""
    # Admin sees all categories (including inactive), regular users only see active
    if current_user.is_authenticated:
        categories = WorkshopCategory.query.order_by(WorkshopCategory.order).all()
    else:
        categories = WorkshopCategory.query.filter_by(is_active=True).order_by(WorkshopCategory.order).all()
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    # Get page title
    page = Page.query.filter_by(slug='angebot').first()
    return render_template('courses/index.html', categories=categories, nav_items=nav_items, page=page)


@bp.route('/kategorie/<int:category_id>')
def workshop_category(category_id):
    """List courses in a workshop category."""
    category = WorkshopCategory.query.get_or_404(category_id)
    courses = Course.query.filter_by(workshop_category_id=category_id, is_active=True).order_by(Course.date.asc()).all()
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/category.html', category=category, courses=courses, nav_items=nav_items)


@bp.route('/<int:course_id>')
def detail(course_id):
    """Course detail page with registration form."""
    course = Course.query.get_or_404(course_id)
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/detail.html', course=course, nav_items=nav_items)


@bp.route('/<int:course_id>/register', methods=['POST'])
@limiter.limit("10 per hour")
def register(course_id):
    """Handle course registration."""
    course = Course.query.get_or_404(course_id)
    
    # Get form data
    vorname = request.form.get('vorname', '').strip()
    name = request.form.get('name', '').strip()
    telefonnummer = request.form.get('telefonnummer', '').strip()
    email = request.form.get('email', '').strip()
    num_participants = int(request.form.get('num_participants', 1))
    
    # Ensure at least 1 participant
    if num_participants < 1:
        num_participants = 1
    
    # Validate required fields
    if not all([vorname, name, telefonnummer]):
        flash('Bitte füllen Sie alle Pflichtfelder aus.', 'error')
        return redirect(url_for('courses.detail', course_id=course_id))
    
    # Validate phone number
    if not validate_phone(telefonnummer):
        flash('Bitte geben Sie eine gültige Telefonnummer ein.', 'error')
        return redirect(url_for('courses.detail', course_id=course_id))
    
    # Validate email if provided
    if email and not validate_email(email):
        flash('Bitte geben Sie eine gültige E-Mail-Adresse ein.', 'error')
        return redirect(url_for('courses.detail', course_id=course_id))
    
    # Calculate how many can be registered vs waitlisted
    spots_available = course.spots_available if course.spots_available is not None else num_participants
    registered_count = min(num_participants, spots_available)
    waitlist_count = num_participants - registered_count
    
    # Create registration for confirmed spots
    if registered_count > 0:
        registration = CourseRegistration(
            course_id=course_id,
            vorname=vorname,
            name=name,
            telefonnummer=telefonnummer,
            email=email if email else None,
            num_participants=registered_count,
            is_waitlist=False
        )
        db.session.add(registration)
        
        # Send confirmation email if email provided
        if email:
            try:
                send_confirmation_email(registration, course)
                registration.confirmation_sent = True
            except Exception as e:
                logger.error(f"Error sending confirmation email: {e}")
        
        # Notify admin
        try:
            notify_admin_registration(registration, course)
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
    
    # Create waitlist entry if overflow
    if waitlist_count > 0:
        waitlist_registration = CourseRegistration(
            course_id=course_id,
            vorname=vorname,
            name=name,
            telefonnummer=telefonnummer,
            email=email if email else None,
            num_participants=waitlist_count,
            is_waitlist=True
        )
        db.session.add(waitlist_registration)
        
        # Notify admin about waitlist
        try:
            notify_admin_registration(waitlist_registration, course)
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
    
    db.session.commit()
    
    # Redirect to appropriate success page
    if waitlist_count > 0 and registered_count > 0:
        # Mixed: some registered, some on waitlist
        return redirect(url_for('courses.mixed_success', course_id=course_id, 
                               registered=registered_count, waitlist=waitlist_count))
    elif waitlist_count > 0:
        # All on waitlist
        return redirect(url_for('courses.waitlist_success', course_id=course_id, count=waitlist_count))
    else:
        # All registered
        return redirect(url_for('courses.registration_success', course_id=course_id, count=registered_count))


@bp.route('/<int:course_id>/gemischt-erfolgreich')
def mixed_success(course_id):
    """Show mixed registration success message (some registered, some waitlisted)."""
    course = Course.query.get_or_404(course_id)
    registered = request.args.get('registered', 1, type=int)
    waitlist = request.args.get('waitlist', 0, type=int)
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/mixed_success.html', course=course, 
                          registered=registered, waitlist=waitlist, nav_items=nav_items)


@bp.route('/<int:course_id>/warteliste-erfolgreich')
def waitlist_success(course_id):
    """Show waitlist success message."""
    course = Course.query.get_or_404(course_id)
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/waitlist_success.html', course=course, nav_items=nav_items)


@bp.route('/<int:course_id>/anmeldung-erfolgreich')
def registration_success(course_id):
    """Show registration success message."""
    course = Course.query.get_or_404(course_id)
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/registration_success.html', course=course, nav_items=nav_items)


def send_confirmation_email(registration, course):
    """Send confirmation email to participant."""
    subject = f'Anmeldebestätigung: {course.title}'
    
    body = f"""
Liebe/r {registration.vorname} {registration.name},

vielen Dank für Ihre Anmeldung zum Kurs "{course.title}".

Kursdetails:
{course.description or ''}

Datum: {course.date.strftime('%d.%m.%Y %H:%M') if course.date else 'Wird noch bekannt gegeben'}
Ort: {course.location or 'Wird noch bekannt gegeben'}

Wir freuen uns auf Sie!

Mit freundlichen Grüssen,
Beatrice Gugger
"""
    
    msg = Message(
        subject=subject,
        recipients=[registration.email],
        body=body
    )
    
    mail.send(msg)


def notify_admin_registration(registration, course):
    """Send notification to admin about a new registration."""
    admin_email = current_app.config.get('ADMIN_EMAIL')
    if not admin_email:
        return

    subject = f'Neue Kursanmeldung: {course.title}'
    body = f"""
Neue Anmeldung eingegangen:

Kurs: {course.title}
Teilnehmer: {registration.vorname} {registration.name}
Telefon: {registration.telefonnummer}
Email: {registration.email or 'n/a'}

Zur Verwaltung: {url_for('admin.course_registrations', course_id=course.id, _external=True)}
"""

    msg = Message(
        subject=subject,
        recipients=[admin_email],
        body=body,
        reply_to=registration.email or None
    )
    mail.send(msg)
