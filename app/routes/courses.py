"""Course routes (listing, detail, registration)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app import db, mail
from app.models import Course, CourseRegistration, NavigationItem
from flask_mail import Message
import os

bp = Blueprint('courses', __name__, url_prefix='/angebot')


@bp.route('/')
def index():
    """List all active courses."""
    courses = Course.query.filter_by(is_active=True).order_by(Course.date.desc()).all()
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/index.html', courses=courses, nav_items=nav_items)


@bp.route('/<int:course_id>')
def detail(course_id):
    """Course detail page with registration form."""
    course = Course.query.get_or_404(course_id)
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/detail.html', course=course, nav_items=nav_items)


@bp.route('/<int:course_id>/register', methods=['POST'])
def register(course_id):
    """Handle course registration."""
    course = Course.query.get_or_404(course_id)
    
    # Check if course is full
    if course.is_full:
        flash('Dieser Kurs ist bereits voll.', 'error')
        return redirect(url_for('courses.detail', course_id=course_id))
    
    # Get form data
    vorname = request.form.get('vorname', '').strip()
    name = request.form.get('name', '').strip()
    telefonnummer = request.form.get('telefonnummer', '').strip()
    email = request.form.get('email', '').strip()
    
    # Validate required fields
    if not all([vorname, name, telefonnummer]):
        flash('Bitte füllen Sie alle Pflichtfelder aus.', 'error')
        return redirect(url_for('courses.detail', course_id=course_id))
    
    # Create registration
    registration = CourseRegistration(
        course_id=course_id,
        vorname=vorname,
        name=name,
        telefonnummer=telefonnummer,
        email=email if email else None
    )
    
    db.session.add(registration)
    db.session.commit()
    
    # Send confirmation email if email provided
    if email:
        try:
            send_confirmation_email(registration, course)
            registration.confirmation_sent = True
            db.session.commit()
        except Exception as e:
            print(f"Error sending email: {e}")

    # Notify admin
    try:
        notify_admin_registration(registration, course)
    except Exception as e:
        print(f"Error notifying admin: {e}")
    
    flash('Vielen Dank für Ihre Anmeldung!', 'success')
    return redirect(url_for('courses.detail', course_id=course_id))


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
