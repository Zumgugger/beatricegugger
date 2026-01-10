"""Admin routes and authentication."""
import logging
import re
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app.models import User, Course, CourseRegistration, ArtCategory, ArtImage, Page, NavigationItem, WorkshopCategory, LocationMapping, MessageTemplate
from app.services.messaging import send_promoted_message
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')


def validate_phone(phone: str) -> bool:
    """Validate phone number - flexible format allowing Swiss/international numbers."""
    if not phone:
        return False
    # Remove all formatting characters: spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Allow optional + at start, then 9-15 digits
    return bool(re.match(r'^\+?\d{9,15}$', cleaned))


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return True  # Email is optional
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(pattern, email))


def allowed_file(filename: str) -> bool:
    """Check allowed file extensions."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', set())


def save_file(file_storage, subfolder: str) -> Optional[str]:
    """Save an uploaded file and return relative path inside uploads."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        flash('Ungültiger Dateityp. Erlaubt sind png/jpg/jpeg/gif.', 'error')
        return None
    filename = secure_filename(file_storage.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    filename = f"{timestamp}_{filename}"
    upload_root: Path = current_app.config['UPLOAD_FOLDER']
    target_dir = upload_root / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / filename
    file_storage.save(str(file_path))
    return f"{subfolder}/{filename}"


# --- Inline editing API ---


@bp.route('/api/page/<int:page_id>/content', methods=['POST'])
@login_required
def update_page_content(page_id: int):
    """Update page content or title inline."""
    page = Page.query.get_or_404(page_id)
    data = request.get_json(silent=True) or {}
    content = data.get('content')
    title = data.get('title')

    if content is not None:
        page.content = content.strip()
    if title is not None:
        page.title = title.strip()
    db.session.commit()
    return {"success": True}


@bp.route('/api/page/<int:page_id>/image', methods=['POST'])
@login_required
def update_page_image(page_id: int):
    """Update page image inline."""
    page = Page.query.get_or_404(page_id)
    image_file = request.files.get('image')
    saved = save_file(image_file, 'pages') if image_file else None
    if saved:
        page.image_path = saved
        db.session.commit()
        return {"success": True, "image_path": saved}
    return {"success": False, "message": "Kein Bild hochgeladen"}, 400


@bp.route('/api/course/<int:course_id>/content', methods=['POST'])
@login_required
def update_course_content(course_id: int):
    """Update course description or title inline."""
    course = Course.query.get_or_404(course_id)
    data = request.get_json(silent=True) or {}
    content = data.get('content')
    title = data.get('title')

    if content is not None:
        course.description = content.strip()
    if title is not None:
        course.title = title.strip()
    db.session.commit()
    return {"success": True}


@bp.route('/api/course', methods=['POST'])
@login_required
def api_create_course():
    """Create a new course via form submission."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    date_str = request.form.get('date')
    location = request.form.get('location', '').strip()
    max_participants = request.form.get('max_participants')
    is_active = bool(request.form.get('is_active'))
    
    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('courses.index'))
    
    image_file = request.files.get('image')
    image_path = save_file(image_file, 'courses') if image_file and image_file.filename else None
    
    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass
    
    course = Course(
        title=title,
        description=description,
        date=parsed_date,
        location=location,
        max_participants=int(max_participants) if max_participants else None,
        is_active=is_active,
        image_path=image_path,
    )
    db.session.add(course)
    db.session.commit()
    flash('Kurs wurde erstellt.', 'success')
    return redirect(url_for('courses.index'))


@bp.route('/api/course/<int:course_id>', methods=['GET'])
@login_required
def api_get_course(course_id: int):
    """Get course data for editing."""
    course = Course.query.get_or_404(course_id)
    return {
        "success": True,
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description or "",
            "date": course.date.strftime('%Y-%m-%d') if course.date else "",
            "time_info": course.time_info or "",
            "cost": course.cost or "",
            "location": course.location or "",
            "location_url": course.location_url or "",
            "max_participants": course.max_participants or ""
        }
    }


@bp.route('/api/course/<int:course_id>', methods=['PUT'])
@login_required
def api_update_course(course_id: int):
    """Update a course via AJAX."""
    from flask import jsonify
    course = Course.query.get_or_404(course_id)
    data = request.get_json(silent=True) or {}
    
    if 'title' in data:
        course.title = data['title'].strip()
    if 'description' in data:
        course.description = data['description'].strip() if data['description'] else None
    if 'date' in data and data['date']:
        try:
            course.date = datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            pass
    if 'time_info' in data:
        course.time_info = data['time_info'].strip() if data['time_info'] else None
    if 'cost' in data:
        course.cost = data['cost'].strip() if data['cost'] else None
    if 'location' in data:
        course.location = data['location'].strip() if data['location'] else None
    if 'location_url' in data:
        course.location_url = data['location_url'].strip() if data['location_url'] else None
    if 'max_participants' in data:
        course.max_participants = int(data['max_participants']) if data['max_participants'] else None
    
    # Save location mapping if both provided
    location = course.location
    location_url = course.location_url
    if location and location_url:
        existing_mapping = LocationMapping.query.filter_by(address=location).first()
        if existing_mapping:
            existing_mapping.google_maps_url = location_url
        else:
            new_mapping = LocationMapping(address=location, google_maps_url=location_url)
            db.session.add(new_mapping)
    
    db.session.commit()
    return jsonify({"success": True, "message": "Kurs aktualisiert"})


@bp.route('/api/course/<int:course_id>', methods=['DELETE'])
@login_required
def api_delete_course(course_id: int):
    """Delete a course via AJAX."""
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    return {"success": True}


@bp.route('/api/course/<int:course_id>/image', methods=['POST'])
@login_required
def update_course_image(course_id: int):
    """Update course image inline."""
    course = Course.query.get_or_404(course_id)
    image_file = request.files.get('image')
    saved = save_file(image_file, 'courses') if image_file else None
    if saved:
        course.image_path = saved
        db.session.commit()
        return {"success": True, "image_path": saved}
    return {"success": False, "message": "Kein Bild hochgeladen"}, 400


@bp.route('/api/art-category/<int:category_id>/content', methods=['POST'])
@login_required
def update_art_category_content(category_id: int):
    """Update art category title/description inline."""
    category = ArtCategory.query.get_or_404(category_id)
    data = request.get_json(silent=True) or {}
    title = data.get('title')
    description = data.get('description')

    if title is not None:
        category.title = title.strip()
    if description is not None:
        category.description = description.strip()
    db.session.commit()
    return {"success": True}


@bp.route('/api/art-category/<int:category_id>/image', methods=['POST'])
@login_required
def update_art_category_image(category_id: int):
    """Update art category featured image inline."""
    category = ArtCategory.query.get_or_404(category_id)
    image_file = request.files.get('image')
    saved = save_file(image_file, 'art') if image_file else None
    if saved:
        category.featured_image_path = saved
        db.session.commit()
        return {"success": True, "image_path": saved}
    return {"success": False, "message": "Kein Bild hochgeladen"}, 400


@bp.route('/api/art-category', methods=['POST'])
@login_required
def api_create_art_category():
    """Create a new art category via form submission."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    order = request.form.get('order', 0)
    is_active = bool(request.form.get('is_active'))
    
    featured_image = request.files.get('featured_image')
    image_path = save_file(featured_image, 'art') if featured_image and featured_image.filename else None
    
    category = ArtCategory(
        title=title,
        description=description,
        order=int(order) if order else 0,
        is_active=is_active,
        featured_image_path=image_path,
    )
    db.session.add(category)
    db.session.commit()
    flash('Kategorie wurde erstellt.', 'success')
    return redirect(url_for('art.index'))


@bp.route('/api/art-category/<int:category_id>', methods=['DELETE'])
@login_required
def api_delete_art_category(category_id: int):
    """Delete an art category via AJAX."""
    category = ArtCategory.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return {"success": True}


@bp.route('/api/art-categories/reorder', methods=['POST'])
@login_required
def api_reorder_art_categories():
    """Reorder art categories via drag and drop."""
    data = request.get_json()
    order_data = data.get('order', [])
    
    for item in order_data:
        category = ArtCategory.query.get(item['id'])
        if category:
            category.order = item['order']
    
    db.session.commit()
    return jsonify({"success": True})


@bp.route('/api/art-category/<int:category_id>/images', methods=['POST'])
@login_required
def api_upload_art_images(category_id: int):
    """Upload one or more images to an art category."""
    category = ArtCategory.query.get_or_404(category_id)
    images = request.files.getlist('images')
    caption = request.form.get('caption', '').strip()
    
    if not images:
        flash('Keine Bilder ausgewählt.', 'error')
        return redirect(url_for('art.gallery', category_id=category_id))
    
    uploaded_count = 0
    max_order = db.session.query(db.func.max(ArtImage.order)).filter_by(category_id=category_id).scalar() or 0
    
    for image_file in images:
        if image_file and image_file.filename:
            saved = save_file(image_file, 'art')
            if saved:
                max_order += 1
                art_image = ArtImage(
                    category_id=category_id,
                    image_path=saved,
                    caption=caption if caption else None,
                    order=max_order,
                )
                db.session.add(art_image)
                uploaded_count += 1
    
    db.session.commit()
    flash(f'{uploaded_count} Bild(er) hochgeladen.', 'success')
    return redirect(url_for('art.gallery', category_id=category_id))


@bp.route('/api/art-image/<int:image_id>', methods=['DELETE'])
@login_required
def api_delete_art_image(image_id: int):
    """Delete an art image via AJAX."""
    image = ArtImage.query.get_or_404(image_id)
    db.session.delete(image)
    db.session.commit()
    return {"success": True}


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """Admin login page."""
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            logger.info(f"Successful login for user: {email}")
            login_user(user, remember=True)
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('public.index'))
        else:
            logger.warning(f"Failed login attempt for email: {email}")
            flash('Ungültige E-Mail oder Passwort.', 'error')
    
    return render_template('admin/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Logout admin user."""
    logout_user()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('public.index'))


@bp.route('/admin_users')
@login_required
def admin_users():
    """Manage admin users."""
    users = User.query.order_by(User.created_at.desc()).all()
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('admin/users.html', users=users, nav_items=nav_items)


@bp.route('/api/user', methods=['POST'])
@login_required
def api_create_user():
    """Create a new admin user."""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not name or not email or not password:
        return jsonify({'success': False, 'error': 'Alle Felder sind erforderlich'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Passwort muss mindestens 6 Zeichen lang sein'}), 400
    
    if not validate_email(email):
        return jsonify({'success': False, 'error': 'Ungültige E-Mail-Adresse'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'E-Mail-Adresse bereits vergeben'}), 400
    
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': True, 'user_id': user.id})


@bp.route('/api/user/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    """Update an admin user."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not name or not email:
        return jsonify({'success': False, 'error': 'Name und E-Mail sind erforderlich'}), 400
    
    if not validate_email(email):
        return jsonify({'success': False, 'error': 'Ungültige E-Mail-Adresse'}), 400
    
    # Check if email already exists for another user
    existing = User.query.filter_by(email=email).first()
    if existing and existing.id != user_id:
        return jsonify({'success': False, 'error': 'E-Mail-Adresse bereits vergeben'}), 400
    
    user.name = name
    user.email = email
    
    if password:
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Passwort muss mindestens 6 Zeichen lang sein'}), 400
        user.set_password(password)
    
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/user/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """Delete an admin user."""
    # Prevent self-deletion
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Du kannst dich nicht selbst löschen'}), 400
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/message_templates')
@login_required
def message_templates():
    """Manage message templates."""
    templates = MessageTemplate.query.order_by(
        MessageTemplate.message_type,
        MessageTemplate.trigger
    ).all()
    
    trigger_labels = {
        'registration_confirmed': 'Anmeldung bestätigt',
        'registration_mixed': 'Teilweise Warteliste',
        'registration_waitlist': 'Warteliste',
        'promoted_from_waitlist': 'Von Warteliste angemeldet',
        'reminder_1day': 'Erinnerung (1 Tag vorher)',
        'admin_new_registration': 'Admin-Benachrichtigung (neue Anmeldung)'
    }
    
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('admin/message_templates.html', 
                          templates=templates, 
                          trigger_labels=trigger_labels,
                          nav_items=nav_items)


@bp.route('/api/message-template/<int:template_id>', methods=['PUT'])
@login_required
def api_update_message_template(template_id):
    """Update a message template."""
    template = MessageTemplate.query.get_or_404(template_id)
    data = request.get_json()
    
    template.body = data.get('body', template.body)
    template.is_active = data.get('is_active', template.is_active)
    
    if template.message_type == 'email':
        template.subject = data.get('subject', template.subject)
    
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/')
@login_required
def dashboard():
    """Redirect to homepage - admin functions are now in-place."""
    return redirect(url_for('public.index'))
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


@bp.route('/courses/create', methods=['POST'])
@login_required
def create_course():
    """Create a new course."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    date_str = request.form.get('date')
    location = request.form.get('location', '').strip()
    max_participants = request.form.get('max_participants')
    is_active = bool(request.form.get('is_active'))
    image_path = None

    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('admin.courses'))

    image_file = request.files.get('image')
    if image_file and image_file.filename:
        saved = save_file(image_file, 'courses')
        image_path = saved or None

    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Ungültiges Datumsformat. Bitte Datum/Zeit neu eingeben.', 'error')
            return redirect(url_for('admin.courses'))

    course = Course(
        title=title,
        description=description,
        date=parsed_date,
        location=location,
        max_participants=int(max_participants) if max_participants else None,
        is_active=is_active,
        image_path=image_path,
    )

    db.session.add(course)
    db.session.commit()
    flash('Kurs wurde erstellt.', 'success')
    return redirect(url_for('admin.courses'))


@bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    """Edit an existing course."""
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        date_str = request.form.get('date')
        location = request.form.get('location', '').strip()
        max_participants = request.form.get('max_participants')
        is_active = bool(request.form.get('is_active'))

        if not title:
            flash('Titel ist erforderlich.', 'error')
            return redirect(url_for('admin.edit_course', course_id=course_id))

        parsed_date = None
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Ungültiges Datumsformat. Bitte Datum/Zeit neu eingeben.', 'error')
                return redirect(url_for('admin.edit_course', course_id=course_id))

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            saved = save_file(image_file, 'courses')
            if saved:
                course.image_path = saved

        course.title = title
        course.description = description
        course.date = parsed_date
        course.location = location
        course.max_participants = int(max_participants) if max_participants else None
        course.is_active = is_active

        db.session.commit()
        flash('Kurs wurde aktualisiert.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_edit.html', course=course)


@bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    """Delete a course."""
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Kurs wurde gelöscht.', 'info')
    return redirect(url_for('admin.courses'))


@bp.route('/courses/<int:course_id>/registrations')
@login_required
def course_registrations(course_id):
    """View registrations for a specific course."""
    course = Course.query.get_or_404(course_id)
    registrations = course.registrations.order_by(CourseRegistration.registered_at.desc()).all()
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('courses/registrations.html', course=course, registrations=registrations, nav_items=nav_items)


@bp.route('/api/registration/<int:registration_id>', methods=['DELETE'])
@login_required
def api_delete_registration(registration_id):
    """Delete a registration."""
    from app.models import ScheduledMessage
    registration = CourseRegistration.query.get_or_404(registration_id)
    # Delete any scheduled messages for this registration first
    ScheduledMessage.query.filter_by(registration_id=registration_id).delete()
    db.session.delete(registration)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/registration/<int:registration_id>/promote', methods=['POST'])
@login_required
def api_promote_registration(registration_id):
    """Move a registration from waitlist to registered."""
    registration = CourseRegistration.query.get_or_404(registration_id)
    
    if not registration.is_waitlist:
        return jsonify({'success': False, 'error': 'Diese Person ist bereits angemeldet'}), 400
    
    course = registration.course
    spots_available = course.spots_available
    
    if spots_available <= 0:
        return jsonify({'success': False, 'error': 'Keine freien Plätze verfügbar'}), 400
    
    # If the registration has more participants than available spots, we can only promote some
    num_participants = registration.num_participants or 1
    if num_participants <= spots_available:
        # Promote entire registration
        registration.is_waitlist = False
        db.session.commit()
        
        # Send promotion notification
        try:
            send_promoted_message(registration)
        except Exception as e:
            logger.error(f"Error sending promotion notification: {e}")
        
        return jsonify({'success': True, 'message': f'{num_participants} Person(en) angemeldet'})
    else:
        # Split the registration: promote available spots, keep rest on waitlist
        registration.num_participants = num_participants - spots_available
        
        # Create new registration for the promoted spots
        new_reg = CourseRegistration(
            course_id=course.id,
            vorname=registration.vorname,
            name=registration.name,
            telefonnummer=registration.telefonnummer,
            email=registration.email,
            num_participants=spots_available,
            is_waitlist=False
        )
        db.session.add(new_reg)
        db.session.commit()
        
        # Send promotion notification for the promoted registration
        try:
            send_promoted_message(new_reg)
        except Exception as e:
            logger.error(f"Error sending promotion notification: {e}")
        
        return jsonify({'success': True, 'message': f'{spots_available} Person(en) angemeldet, {registration.num_participants} bleiben auf der Warteliste'})


@bp.route('/api/registration/<int:registration_id>', methods=['PUT'])
@login_required
def api_update_registration(registration_id):
    """Update a registration."""
    registration = CourseRegistration.query.get_or_404(registration_id)
    data = request.get_json()
    
    telefonnummer = data.get('telefonnummer', registration.telefonnummer)
    email = data.get('email') or None
    num_participants = data.get('num_participants', registration.num_participants)
    
    # Validate phone
    if not validate_phone(telefonnummer):
        return jsonify({'success': False, 'error': 'Ungültige Telefonnummer'}), 400
    
    # Validate email if provided
    if email and not validate_email(email):
        return jsonify({'success': False, 'error': 'Ungültige E-Mail-Adresse'}), 400
    
    # Validate num_participants
    if num_participants < 1:
        num_participants = 1
    
    registration.vorname = data.get('vorname', registration.vorname)
    registration.name = data.get('name', registration.name)
    registration.telefonnummer = telefonnummer
    registration.email = email
    registration.num_participants = num_participants
    
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/course/<int:course_id>/registration', methods=['POST'])
@login_required
def api_create_registration(course_id):
    """Create a new registration for a course."""
    course = Course.query.get_or_404(course_id)
    data = request.get_json()
    
    telefonnummer = data.get('telefonnummer', '').strip()
    email = data.get('email') or None
    
    # Validate phone
    if not validate_phone(telefonnummer):
        return jsonify({'success': False, 'error': 'Ungültige Telefonnummer'}), 400
    
    # Validate email if provided
    if email and not validate_email(email):
        return jsonify({'success': False, 'error': 'Ungültige E-Mail-Adresse'}), 400
    
    registration = CourseRegistration(
        course_id=course_id,
        vorname=data.get('vorname', '').strip(),
        name=data.get('name', '').strip(),
        telefonnummer=telefonnummer,
        email=email
    )
    
    db.session.add(registration)
    db.session.commit()
    return jsonify({'success': True, 'id': registration.id})


@bp.route('/art')
@login_required
def art():
    """Manage art categories."""
    categories = ArtCategory.query.order_by(ArtCategory.order).all()
    return render_template('admin/art.html', categories=categories)


@bp.route('/art', methods=['POST'])
@login_required
def create_art_category():
    """Create a new art category."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    order = request.form.get('order', 0)
    is_active = bool(request.form.get('is_active'))
    featured_image = request.files.get('featured_image')

    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('admin.art'))

    image_path = None
    if featured_image and featured_image.filename:
        image_path = save_file(featured_image, 'art')

    category = ArtCategory(
        title=title,
        description=description,
        order=int(order) if order else 0,
        is_active=is_active,
        featured_image_path=image_path,
    )
    db.session.add(category)
    db.session.commit()
    flash('Kategorie erstellt.', 'success')
    return redirect(url_for('admin.art'))


@bp.route('/art/<int:category_id>/update', methods=['POST'])
@login_required
def update_art_category(category_id):
    """Update an art category."""
    category = ArtCategory.query.get_or_404(category_id)
    title = request.form.get('title', '').strip()
    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('admin.art'))

    category.title = title
    category.description = request.form.get('description', '').strip()
    category.order = int(request.form.get('order', category.order) or category.order)
    category.is_active = bool(request.form.get('is_active'))

    featured_image = request.files.get('featured_image')
    if featured_image and featured_image.filename:
        saved = save_file(featured_image, 'art')
        if saved:
            category.featured_image_path = saved

    db.session.commit()
    flash('Kategorie aktualisiert.', 'success')
    return redirect(url_for('admin.art'))


@bp.route('/art/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_art_category(category_id):
    """Delete an art category."""
    category = ArtCategory.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Kategorie gelöscht.', 'info')
    return redirect(url_for('admin.art'))


@bp.route('/art/<int:category_id>/images', methods=['GET', 'POST'])
@login_required
def manage_art_images(category_id):
    """Manage images for a category."""
    category = ArtCategory.query.get_or_404(category_id)

    if request.method == 'POST':
        image_file = request.files.get('image')
        caption = request.form.get('caption', '').strip()
        order = request.form.get('order', 0)

        saved = save_file(image_file, 'art') if image_file else None
        if saved:
            art_image = ArtImage(
                category_id=category.id,
                image_path=saved,
                caption=caption,
                order=int(order) if order else 0,
            )
            db.session.add(art_image)
            db.session.commit()
            flash('Bild hinzugefügt.', 'success')
        else:
            flash('Bitte ein Bild auswählen.', 'error')

        return redirect(url_for('admin.manage_art_images', category_id=category_id))

    images = category.images.order_by(ArtImage.order).all()
    return render_template('admin/art_images.html', category=category, images=images)


@bp.route('/art/images/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_art_image(image_id):
    """Delete an art image."""
    image = ArtImage.query.get_or_404(image_id)
    category_id = image.category_id
    db.session.delete(image)
    db.session.commit()
    flash('Bild gelöscht.', 'info')
    return redirect(url_for('admin.manage_art_images', category_id=category_id))


@bp.route('/pages')
@login_required
def pages():
    """Manage pages."""
    pages = Page.query.all()
    return render_template('admin/pages.html', pages=pages)


@bp.route('/pages', methods=['POST'])
@login_required
def create_page():
    """Create a new page."""
    title = request.form.get('title', '').strip()
    slug = request.form.get('slug', '').strip()
    content = request.form.get('content', '').strip()
    image = request.files.get('image')

    if not title or not slug:
        flash('Titel und Slug sind erforderlich.', 'error')
        return redirect(url_for('admin.pages'))

    image_path = None
    if image and image.filename:
        image_path = save_file(image, 'pages')

    page = Page(title=title, slug=slug, content=content, image_path=image_path)
    db.session.add(page)
    db.session.commit()
    flash('Seite erstellt.', 'success')
    return redirect(url_for('admin.pages'))


@bp.route('/pages/<int:page_id>/update', methods=['POST'])
@login_required
def update_page(page_id):
    """Update existing page."""
    page = Page.query.get_or_404(page_id)
    title = request.form.get('title', '').strip()
    slug = request.form.get('slug', '').strip()
    content = request.form.get('content', '').strip()

    if not title or not slug:
        flash('Titel und Slug sind erforderlich.', 'error')
        return redirect(url_for('admin.pages'))

    page.title = title
    page.slug = slug
    page.content = content

    image = request.files.get('image')
    if image and image.filename:
        saved = save_file(image, 'pages')
        if saved:
            page.image_path = saved

    db.session.commit()
    flash('Seite aktualisiert.', 'success')
    return redirect(url_for('admin.pages'))


@bp.route('/pages/<int:page_id>/delete', methods=['POST'])
@login_required
def delete_page(page_id):
    """Delete a page."""
    page = Page.query.get_or_404(page_id)
    db.session.delete(page)
    db.session.commit()
    flash('Seite gelöscht.', 'info')
    return redirect(url_for('admin.pages'))


@bp.route('/navigation')
@login_required
def navigation():
    """Manage navigation items."""
    nav_items = NavigationItem.query.order_by(NavigationItem.order).all()
    return render_template('admin/navigation.html', nav_items=nav_items)


@bp.route('/navigation', methods=['POST'])
@login_required
def create_navigation():
    """Create a navigation item."""
    title = request.form.get('title', '').strip()
    slug = request.form.get('slug', '').strip()
    order = request.form.get('order', 0)
    is_active = bool(request.form.get('is_active'))
    icon_file = request.files.get('icon')

    if not title or not slug:
        flash('Titel und Slug sind erforderlich.', 'error')
        return redirect(url_for('admin.navigation'))

    icon_path = None
    if icon_file and icon_file.filename:
        icon_path = save_file(icon_file, 'navigation')

    nav_item = NavigationItem(
        title=title,
        slug=slug,
        order=int(order) if order else 0,
        is_active=is_active,
        icon_path=icon_path,
    )
    db.session.add(nav_item)
    db.session.commit()
    flash('Navigationseintrag erstellt.', 'success')
    return redirect(url_for('admin.navigation'))


@bp.route('/navigation/<int:item_id>/update', methods=['POST'])
@login_required
def update_navigation(item_id):
    """Update a navigation item."""
    nav_item = NavigationItem.query.get_or_404(item_id)
    title = request.form.get('title', '').strip()
    slug = request.form.get('slug', '').strip()

    if not title or not slug:
        flash('Titel und Slug sind erforderlich.', 'error')
        return redirect(url_for('admin.navigation'))

    nav_item.title = title
    nav_item.slug = slug
    nav_item.order = int(request.form.get('order', nav_item.order) or nav_item.order)
    nav_item.is_active = bool(request.form.get('is_active'))

    icon_file = request.files.get('icon')
    if icon_file and icon_file.filename:
        saved = save_file(icon_file, 'navigation')
        if saved:
            nav_item.icon_path = saved

    db.session.commit()
    flash('Navigationseintrag aktualisiert.', 'success')
    return redirect(url_for('admin.navigation'))


@bp.route('/navigation/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_navigation(item_id):
    """Delete a navigation item."""
    nav_item = NavigationItem.query.get_or_404(item_id)
    db.session.delete(nav_item)
    db.session.commit()
    flash('Navigationseintrag gelöscht.', 'info')
    return redirect(url_for('admin.navigation'))


@bp.route('/api/navigation/reorder', methods=['POST'])
@login_required
def api_reorder_navigation():
    """Reorder navigation items."""
    data = request.get_json(silent=True) or {}
    order_list = data.get('order', [])
    for item in order_list:
        nav_item = NavigationItem.query.get(item['id'])
        if nav_item:
            nav_item.order = item['order']
    db.session.commit()
    return {"success": True}


# --- Workshop Category API Routes ---


@bp.route('/api/workshop-category', methods=['POST'])
@login_required
def api_create_workshop_category():
    """Create a new workshop category via form submission."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('courses.index'))
    
    image_file = request.files.get('image')
    image_path = save_file(image_file, 'courses') if image_file and image_file.filename else None
    
    # Get max order
    max_order = db.session.query(db.func.max(WorkshopCategory.order)).scalar() or 0
    
    category = WorkshopCategory(
        title=title,
        description=description,
        image_path=image_path,
        card_image_path=image_path,  # Same image for both by default
        order=max_order + 1,
        is_active=True,
    )
    db.session.add(category)
    db.session.commit()
    flash('Workshop-Kategorie wurde erstellt.', 'success')
    return redirect(url_for('courses.index'))


@bp.route('/api/workshop-category/<int:category_id>', methods=['DELETE'])
@login_required
def api_delete_workshop_category(category_id):
    """Delete a workshop category via AJAX."""
    category = WorkshopCategory.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return {"success": True}


@bp.route('/api/workshop-category/<int:category_id>/toggle', methods=['POST'])
@login_required
def api_toggle_workshop_category(category_id):
    """Toggle workshop category is_active status."""
    category = WorkshopCategory.query.get_or_404(category_id)
    data = request.get_json(silent=True) or {}
    is_active = data.get('is_active', True)
    category.is_active = is_active
    db.session.commit()
    return {"success": True, "is_active": category.is_active}


@bp.route('/api/workshop-categories/reorder', methods=['POST'])
@login_required
def api_reorder_workshop_categories():
    """Reorder workshop categories."""
    data = request.get_json(silent=True) or {}
    order_list = data.get('order', [])
    for item in order_list:
        category = WorkshopCategory.query.get(item['id'])
        if category:
            category.order = item['order']
    db.session.commit()
    return {"success": True}


@bp.route('/api/workshop-category/<int:category_id>/content', methods=['POST'])
@login_required
def update_workshop_category_content(category_id):
    """Update workshop category title/description inline."""
    category = WorkshopCategory.query.get_or_404(category_id)
    data = request.get_json(silent=True) or {}
    title = data.get('title')
    description = data.get('description')

    if title is not None:
        category.title = title.strip()
    if description is not None:
        category.description = description.strip()
    db.session.commit()
    return {"success": True}


@bp.route('/api/workshop-category/<int:category_id>/image', methods=['POST'])
@login_required
def update_workshop_category_image(category_id):
    """Update workshop category header image (detail page)."""
    category = WorkshopCategory.query.get_or_404(category_id)
    image_file = request.files.get('image')
    saved = save_file(image_file, 'courses') if image_file else None
    if saved:
        category.image_path = saved
        db.session.commit()
        return {"success": True, "image_path": saved}
    return {"success": False, "message": "Kein Bild hochgeladen"}, 400


@bp.route('/api/workshop-category/<int:category_id>/card-image', methods=['POST'])
@login_required
def update_workshop_category_card_image(category_id):
    """Update workshop category card image (overview page)."""
    category = WorkshopCategory.query.get_or_404(category_id)
    image_file = request.files.get('image')
    saved = save_file(image_file, 'courses') if image_file else None
    if saved:
        category.card_image_path = saved
        db.session.commit()
        return {"success": True, "image_path": saved}
    return {"success": False, "message": "Kein Bild hochgeladen"}, 400


@bp.route('/api/workshop-category/<int:category_id>/course', methods=['POST'])
@login_required
def api_create_course_in_category(category_id):
    """Create a new course within a workshop category."""
    category = WorkshopCategory.query.get_or_404(category_id)
    
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    date_str = request.form.get('date')
    time_info = request.form.get('time_info', '').strip()
    cost = request.form.get('cost', '').strip()
    location = request.form.get('location', '').strip()
    location_url = request.form.get('location_url', '').strip()
    max_participants = request.form.get('max_participants')
    
    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('courses.workshop_category', category_id=category_id))
    
    image_file = request.files.get('image')
    image_path = save_file(image_file, 'courses') if image_file and image_file.filename else None
    
    parsed_date = None
    if date_str:
        try:
            # Try date-only format first (from date input)
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                # Try datetime-local format as fallback
                parsed_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
    
    course = Course(
        workshop_category_id=category_id,
        title=title,
        description=description,
        date=parsed_date,
        time_info=time_info if time_info else None,
        cost=cost if cost else None,
        location=location if location else None,
        location_url=location_url if location_url else None,
        max_participants=int(max_participants) if max_participants else None,
        is_active=True,
        image_path=image_path,
    )
    db.session.add(course)
    
    # Save location mapping if both location and location_url are provided
    if location and location_url:
        existing_mapping = LocationMapping.query.filter_by(address=location).first()
        if existing_mapping:
            existing_mapping.google_maps_url = location_url
        else:
            new_mapping = LocationMapping(address=location, google_maps_url=location_url)
            db.session.add(new_mapping)
    
    db.session.commit()
    flash('Kurs wurde erstellt.', 'success')
    return redirect(url_for('courses.workshop_category', category_id=category_id))


# Location Mapping API
@bp.route('/api/location-mapping', methods=['GET'])
@login_required
def api_get_location_mapping():
    """Get Google Maps URL for a given address."""
    from flask import jsonify
    address = request.args.get('address', '').strip()
    if not address:
        return jsonify({'success': False, 'message': 'No address provided'})
    
    mapping = LocationMapping.query.filter_by(address=address).first()
    if mapping:
        return jsonify({'success': True, 'url': mapping.google_maps_url})
    return jsonify({'success': False, 'url': None})


@bp.route('/api/location-mappings', methods=['GET'])
@login_required
def api_get_all_location_mappings():
    """Get all location mappings for autocomplete."""
    from flask import jsonify
    mappings = LocationMapping.query.all()
    result = {m.address: m.google_maps_url for m in mappings}
    return jsonify({'success': True, 'mappings': result})


@bp.route('/api/location-mapping', methods=['POST'])
@login_required
def api_save_location_mapping():
    """Save or update a location mapping."""
    from flask import jsonify
    data = request.get_json()
    address = data.get('address', '').strip()
    url = data.get('url', '').strip()
    
    if not address:
        return jsonify({'success': False, 'message': 'Address required'})
    
    existing = LocationMapping.query.filter_by(address=address).first()
    if existing:
        existing.google_maps_url = url
    else:
        new_mapping = LocationMapping(address=address, google_maps_url=url)
        db.session.add(new_mapping)
    
    # Update all courses with this location to use the new URL
    courses_to_update = Course.query.filter_by(location=address).all()
    for course in courses_to_update:
        course.location_url = url
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Location mapping saved'})
