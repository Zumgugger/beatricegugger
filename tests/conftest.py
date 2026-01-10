import pytest

from app import create_app, db
from app.models import Course, NavigationItem, Page


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Minimal content for nav/page rendering
        nav = NavigationItem(title='About', slug='about-kontakt', order=0, is_active=True)
        page = Page(title='About', slug='about-kontakt', content='Hello world')
        db.session.add_all([nav, page])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def course(app):
    with app.app_context():
        c = Course(title='Testkurs', description='Beschreibung', is_active=True)
        db.session.add(c)
        db.session.commit()
        return c
