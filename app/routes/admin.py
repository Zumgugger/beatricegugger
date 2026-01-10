"""Admin routes and authentication."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Course, CourseRegistration, ArtCategory, ArtImage, Page, NavigationItem
from werkzeug.utils import secure_filename
import os
from pathlib import Path

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.dashboard'))
        else:
            flash('Ungültige E-Mail oder Passwort.', 'error')
    
    return render_template('admin/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Logout admin user."""
    logout_user()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('public.index'))


@bp.route('/')
@login_required
def dashboard():
    """Admin dashboard."""
    # Statistics
    total_courses = Course.query.count()
    total_registrations = CourseRegistration.query.count()
    active_courses = Course.query.filter_by(is_active=True).count()
    recent_registrations = CourseRegistration.query.order_by(CourseRegistration.registered_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         total_courses=total_courses,
                         total_registrations=total_registrations,
                         active_courses=active_courses,
                         recent_registrations=recent_registrations)


@bp.route('/courses')
@login_required
def courses():
    """Manage courses."""
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)


@bp.route('/courses/<int:course_id>/registrations')
@login_required
def course_registrations(course_id):
    """View registrations for a specific course."""
    course = Course.query.get_or_404(course_id)
    registrations = course.registrations.order_by(CourseRegistration.registered_at.desc()).all()
    return render_template('admin/course_registrations.html', course=course, registrations=registrations)


@bp.route('/art')
@login_required
def art():
    """Manage art categories."""
    categories = ArtCategory.query.order_by(ArtCategory.order).all()
    return render_template('admin/art.html', categories=categories)


@bp.route('/pages')
@login_required
def pages():
    """Manage pages."""
    pages = Page.query.all()
    return render_template('admin/pages.html', pages=pages)


@bp.route('/navigation')
@login_required
def navigation():
    """Manage navigation items."""
    nav_items = NavigationItem.query.order_by(NavigationItem.order).all()
    return render_template('admin/navigation.html', nav_items=nav_items)
