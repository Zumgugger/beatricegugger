"""Art gallery routes."""
from flask import Blueprint, render_template
from app.models import ArtCategory, NavigationItem

bp = Blueprint('art', __name__, url_prefix='/art')


@bp.route('/')
def index():
    """List all art categories."""
    categories = ArtCategory.query.filter_by(is_active=True).order_by(ArtCategory.order).all()
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    return render_template('art/index.html', categories=categories, nav_items=nav_items)


@bp.route('/<int:category_id>')
def gallery(category_id):
    """Show gallery for a specific category."""
    category = ArtCategory.query.get_or_404(category_id)
    nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    images = category.images.all()
    return render_template('art/gallery.html', category=category, images=images, nav_items=nav_items)
