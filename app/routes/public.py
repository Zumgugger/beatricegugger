"""Public routes (landing page, about/kontakt)."""
from flask import Blueprint, render_template
from app.models import NavigationItem, Page

bp = Blueprint('public', __name__)


@bp.route('/')
def index():
    """Landing page."""
    try:
        nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    except:
        nav_items = []
    return render_template('public/index.html', nav_items=nav_items)


@bp.route('/about-kontakt')
def about_kontakt():
    """About/Kontakt page."""
    try:
        page = Page.query.filter_by(slug='about-kontakt').first()
        nav_items = NavigationItem.query.filter_by(is_active=True).order_by(NavigationItem.order).all()
    except:
        page = None
        nav_items = []
    return render_template('public/about_kontakt.html', page=page, nav_items=nav_items)
