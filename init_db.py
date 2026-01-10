"""Initialize the database with sample data."""
from app import create_app, db
from app.models import User, NavigationItem, Page
from datetime import datetime

def init_db():
    """Initialize database with default data."""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        if not User.query.filter_by(email='admin@beatricegugger.ch').first():
            # Create default admin user
            admin = User(
                email='admin@beatricegugger.ch',
                name='Admin'
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            print('✓ Created admin user: admin@beatricegugger.ch / admin123')
        
        # Create navigation items
        if NavigationItem.query.count() == 0:
            nav_items = [
                NavigationItem(
                    title='About & Kontakt',
                    slug='about-kontakt',
                    icon_path='About Kontakt grün.png',
                    order=1,
                    is_active=True
                ),
                NavigationItem(
                    title='Angebot',
                    slug='courses.index',
                    icon_path='Angebot braun.png',
                    order=2,
                    is_active=True
                ),
                NavigationItem(
                    title='Art',
                    slug='art',
                    icon_path='Art pink.png',
                    order=3,
                    is_active=True
                )
            ]
            
            for item in nav_items:
                db.session.add(item)
            print('✓ Created navigation items')
        
        # Create About/Kontakt page
        if not Page.query.filter_by(slug='about-kontakt').first():
            about_page = Page(
                slug='about-kontakt',
                title='About & Kontakt',
                content='<p>Willkommen auf meiner Webseite!</p><p>Hier können Sie mehr über mich und meine Arbeit erfahren.</p>',
                updated_at=datetime.utcnow()
            )
            db.session.add(about_page)
            print('✓ Created About/Kontakt page')
        
        db.session.commit()
        print('\n✓ Database initialized successfully!')
        print('\nAdmin login credentials:')
        print('  Email: admin@beatricegugger.ch')
        print('  Password: admin123')
        print('\n⚠️  Please change the admin password after first login!')


if __name__ == '__main__':
    init_db()
