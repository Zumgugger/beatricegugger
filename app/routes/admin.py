"""Admin routes and authentication."""
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Course, CourseRegistration, ArtCategory, ArtImage, Page, NavigationItem, WorkshopCategory
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

bp = Blueprint('admin', __name__, url_prefix='/admin')


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
    
    if not title:
        flash('Titel ist erforderlich.', 'error')
        return redirect(url_for('art.index'))
    
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
def login():
    """Admin login page."""
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print(f"DEBUG LOGIN: email={email}")
        
        user = User.query.filter_by(email=email).first()
        print(f"DEBUG LOGIN: user found={user}")
        
        if user and user.check_password(password):
            print("DEBUG LOGIN: password OK, logging in")
            login_user(user, remember=True)
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            print(f"DEBUG LOGIN: redirecting to {next_page or 'index'}")
            return redirect(next_page or url_for('public.index'))
        else:
            print(f"DEBUG LOGIN: FAILED - user={user}")
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
    return render_template('admin/course_registrations.html', course=course, registrations=registrations)


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
    """Update workshop category image inline."""
    category = WorkshopCategory.query.get_or_404(category_id)
    image_file = request.files.get('image')
    saved = save_file(image_file, 'courses') if image_file else None
    if saved:
        category.image_path = saved
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
    db.session.commit()
    flash('Kurs wurde erstellt.', 'success')
    return redirect(url_for('courses.workshop_category', category_id=category_id))
