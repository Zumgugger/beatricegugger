# Beatrice Gugger Website - Initial Project Plan

**Date:** January 10, 2026  
**Status:** Planning Phase - Awaiting Technical Decisions

---

## 1. Project Overview

A comprehensive website for an artist (Beatrice Gugger) featuring:
- Public-facing website with courses and art galleries
- Admin panel with WYSIWYG editing capabilities
- Course registration system with email and SMS notifications
- Responsive design for mobile, tablet, and desktop

**Domain:** beatricegugger.ch  
**IP Address:** 185.66.108.95

---

## 2. Technical Stack

### Backend
- **Framework:** Flask (Python)
- **Database:** SQLite (sufficient for expected traffic, easy migration path to PostgreSQL if needed)
- **Language:** Python 3.10+
- **ORM:** SQLAlchemy
- **Migration Tool:** Flask-Migrate (Alembic)

### Frontend
- **Framework:** Flask with Jinja2 templates (server-side rendering)
- **JavaScript:** Vanilla JS for interactive components (gallery, hamburger menu, in-place editing)
- **Styling:** Custom CSS, responsive design (mobile-first approach)
- **Assets:** Custom PNG icons and backgrounds

### Services
- **Email:** SMTP (configuration TBD - server mail/Gmail/domain email)
- **SMS:** [TO BE IMPLEMENTED LATER]
- **File Storage:** Local filesystem
  - `/static` - Application assets (custom PNGs, CSS, JS)
  - `/uploads` - User-uploaded content (course images, art gallery, etc.)

---

## 3. Architecture

### 3.1 Application Structure
```
beatricegugger/
├── app/                  # Main Flask application
│   ├── __init__.py      # App factory
│   ├── models.py        # Database models
│   ├── routes/          # Route blueprints
│   │   ├── public.py    # Public pages
│   │   ├── courses.py   # Course pages and registration
│   │   ├── art.py       # Art gallery
│   │   └── admin.py     # Admin panel
│   ├── templates/       # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── public/
│   │   ├── courses/
│   │   ├── art/
│   │   └── admin/
│   ├── static/          # Application assets (CSS, JS, custom PNGs)
│   │   ├── css/
│   │   ├── js/
│   │   └── images/      # Custom PNG icons and backgrounds
│   └── utils/           # Helper functions
├── uploads/             # User-uploaded content (selected via admin)
│   ├── courses/         # Course images
│   ├── art/             # Art gallery images
│   └── pages/           # About/Kontakt images
├── PNGs/                # PROVIDED: Static design assets
│   ├── Hintergrund Seidenpapier.png   # Site background
│   ├── About Kontakt grün.png         # Navigation button
│   ├── Angebot braun.png              # Navigation button
│   ├── Art pink.png                   # Navigation button
│   ├── Blumen Icon 256x256.png        # Site logo
│   └── Blumen Icon 32x32.png          # Favicon
├── migrations/          # Database migrations
├── tests/               # Test suite
├── docs/                # Documentation
├── docker/              # Docker configuration
├── .env.example         # Environment variables template
├── config.py            # Application configuration
├── requirements.txt     # Python dependencies
└── run.py              # Application entry point
```

### 3.2 Database Schema (Draft)

**Core Tables:**
- **Users** - Admin authentication
- **Pages** - Dynamic content pages (About/Kontakt)
- **NavigationItems** - Configurable navigation
- **Courses** - Course offerings
- **CourseRegistrations** - User registrations
- **ArtCategories** - Art gallery categories
- **ArtImages** - Gallery images
- **Settings** - Site-wide configuration

### 3.3 API Endpoints (Draft)

**Public API:**
- `GET /api/navigation` - Get navigation items
- `GET /api/pages/:slug` - Get page content
- `GET /api/courses` - List courses
- `GET /api/courses/:id` - Get course details
- `POST /api/courses/:id/register` - Register for course
- `GET /api/art/categories` - List art categories
- `GET /api/art/categories/:id/images` - Get category images

**Admin API:**
- `POST /api/admin/login` - Authentication
- `PUT /api/admin/navigation/:id` - Update navigation
- `CRUD /api/admin/courses` - Manage courses
- `CRUD /api/admin/art/categories` - Manage categories
- `POST /api/admin/upload` - Upload images
- `GET /api/admin/statistics` - Course statistics

---

## 4. Features Breakdown

### 4.1 Public Website

#### Landing Page
- **Background:** `Hintergrund Seidenpapier.png` (full site background)
- **Logo:** `Blumen Icon 256x256.png` (top left corner)
- **Favicon:** `Blumen Icon 32x32.png`
- **Navigation bar (3 main sections):**
  - "About/Kontakt" - `About Kontakt grün.png`
  - "Angebot" (Courses) - `Angebot braun.png`
  - "Art" - `Art pink.png`
  - Responsive hamburger menu for mobile/tablet
- Clean, minimalist design (no additional styling initially)

#### About/Kontakt Page
- Artist photo (admin-configurable)
- About text (in-place editing)
- Contact links with custom PNG icons
  - Email
  - Phone
  - Social media (if applicable)

#### Angebote (Courses) Page
- Grid/list of available courses
- Each course shows:
  - Featured image
  - Title and description
  - Link to course details

#### Individual Course Page
- Course image
- Detailed description
- Registration form:
  - Required fields: [PENDING USER INPUT]
  - Submit triggers:
    1. Confirmation email to participant
    2. Notification to admin
    3. SMS reminder scheduled
- Edit capabilities in admin panel

#### Art Page
- List of art categories
- Each category:
  - Featured image
  - Description
  - Link to gallery

#### Art Category Gallery
- Image gallery with navigation
- Left/right arrows to browse
- Possibly lightbox/modal view
- Admin can add/remove/reorder images

### 4.2 Admin Panel

**Key Requirements:**
- WYSIWYG experience (no code/technical interface)
- In-place editing where possible
- Drag-and-drop image uploads
- Visual editor for text content

**Admin Features:**
1. **Dashboard**
   - Course registration statistics
   - Recent registrations
   - Quick links to common tasks

2. **Navigation Management**
   - Add/edit/remove navigation items
   - Upload custom PNG icons
   - Drag-and-drop reordering

3. **Page Content Management**
   - Edit About/Kontakt page
   - Upload/change images
   - Rich text editor for content

4. **Course Management**
   - Create/edit/delete courses
   - Upload course images
   - Set course details (date, time, capacity, etc.)
   - View registrations per course
   - Export participant lists

5. **Art Gallery Management**
   - Create/edit/delete categories
   - Upload multiple images at once
   - Drag-and-drop image ordering
   - Edit image captions/metadata

6. **Statistics & Reports**
   - Course popularity metrics
   - Registration trends
   - Export capabilities

### 4.3 Course Registration System

**User Flow:**
1. User fills registration form on course page (Vorname, Name, Telefonnummer)
2. System validates input
3. Creates registration record
4. Sends confirmation email immediately
5. Admin receives notification
6. [SMS reminder functionality to be implemented later]

**Note:** No payment integration needed (Swiss payment culture - cash or invoice)

**Email Template:**
- Confirmation of registration
- Course details
- Date, time, location
- Contact information
- Cancellation policy (if applicable)

**SMS Reminder:**
- Brief reminder message
- Course name and date
- Location

---

## 5. Development Workflow

### 5.1 Local Development
- Python virtual environment (`.venv`)
- SQLite database (local file)
- Flask development server with hot-reloading
- Email debug mode (prints to console instead of sending)

### 5.2 Version Control
- Git repository
- Branch strategy:
  - `main` - production-ready code
  - `develop` - integration branch
  - Feature branches for development

### 5.3 CI/CD Pipeline
- GitHub repository
- Automated testing
- Docker image building
- Deployment to production server

---

## 6. Deployment Architecture

### 6.1 Server Configuration
- **OS:** Ubuntu Server LTS 14 [NOTE: This is quite old - recommend upgrade]
- **Web Server:** Apache2
- **Location:** `/var/www/beatricegugger`
- **Apache Config:** `/etc/apache2`
- **SSL:** Let's Encrypt (Certbot)

### 6.2 Docker Compose Setup
```yaml
# Draft docker-compose.yml structure
services:
  backend:
    # API application
  frontend:
    # Static files / SSR application
  database:
    # Database service
  nginx:
    # Reverse proxy (or use Apache as reverse proxy)
  redis:
    # Session storage / caching (optional)
```

### 6.3 Apache Virtual Host
- Configure reverse proxy to Docker containers
- HTTPS redirect
- SSL certificate configuration
- Static file serving optimization

---

## 7. Security Considerations

- **HTTPS Only:** All traffic via SSL
- **Admin Authentication:** Secure login with session management
- **CSRF Protection:** For all forms
- **Input Validation:** Server-side validation for all inputs
- **SQL Injection Prevention:** Parameterized queries
- **File Upload Validation:** Type and size restrictions
- **Rate Limiting:** Prevent abuse of registration/contact forms
- **Environment Variables:** Sensitive configuration in .env files

---

## 8. Development Phases

### Phase 1: Setup & Foundation (Week 1-2)
- [ ] Finalize technology stack
- [ ] Set up project structure
- [ ] Initialize Git repository
- [ ] Configure development environment
- [ ] Set up database schema
- [ ] Create Docker configuration

### Phase 2: Backend Development (Week 2-4)
- [ ] Implement authentication system
- [ ] Build API endpoints
- [ ] Database models and migrations
- [ ] Email integration
- [ ] SMS integration
- [ ] File upload handling

### Phase 3: Frontend Development (Week 4-6)
- [ ] Responsive layout structure
- [ ] Landing page
- [ ] About/Kontakt page
- [ ] Courses listing and detail pages
- [ ] Art gallery pages
- [ ] Registration forms

### Phase 4: Admin Panel (Week 6-8)
- [ ] Admin authentication
- [ ] Dashboard
- [ ] Content management interfaces
- [ ] Course management
- [ ] Art gallery management
- [ ] WYSIWYG editors integration

### Phase 5: Testing & Refinement (Week 8-9)
- [ ] Unit testing
- [ ] Integration testing
- [ ] User acceptance testing
- [ ] Performance optimization
- [ ] Security audit

### Phase 6: Deployment (Week 9-10)
- [ ] Server preparation
- [ ] Apache configuration
- [ ] SSL certificate setup
- [ ] Docker deployment
- [ ] Database migration
- [ ] DNS configuration
- [ ] Monitoring setup

---

## 9. ~~Open Questions~~ RESOLVED

### ✅ Technical Decisions (Finalized):
1. **Backend framework:** Flask (Python)
2. **Database:** SQLite
3. **Frontend:** Server-side rendering with Jinja2 templates + vanilla JavaScript
4. **Email service:** SMTP (configuration TBD - multiple options available)
5. **SMS service:** To be implemented later
6. **File storage:** Local filesystem (`/static` for app assets, `/uploads` for user content)

### ✅ Feature Clarifications (Finalized):
7. **Admin users:** Multiple admins with same permissions (artist + developer)
8. **Authentication:** Email/password
9. **Language:** German only
10. **Custom PNG assets:** ✅ Added to `/PNGs` folder
    - Site background: `Hintergrund Seidenpapier.png`
    - Navigation: `About Kontakt grün.png`, `Angebot braun.png`, `Art pink.png`
    - Logo: `Blumen Icon 256x256.png`
    - Favicon: `Blumen Icon 32x32.png`
    - All other images selectable via admin interface
11. **Payment integration:** Not needed (Swiss payment culture)
12. **SMS reminder timing:** To be implemented later
13. **Registration fields:** Vorname, Name, Telefonnummer

### 🔄 Pending Items:
- [x] ~~Custom PNG assets~~ ✅ COMPLETE
- [ ] SMS integration (future feature)
- [ ] SMS reminder timing (future feature)
- [ ] Email SMTP configuration details (to be configured during deployment)

---

## 10. Next Steps

1. ✅ ~~Await answers to open questions~~
2. ✅ ~~Update this plan with finalized decisions~~
3. ✅ ~~User adds custom PNG assets to project~~
4. 🚀 **READY TO BEGIN DEVELOPMENT**

### Building Phase - Starting Now:
- Set up project structure and dependencies
- Configure Flask application
- Create database models (Users, Courses, Registrations, Art, Navigation, Pages)
- Implement admin authentication system
- Build base templates with provided PNGs
- Create public routes (landing, about/kontakt, courses, art)
- Build admin panel with WYSIWYG editing
- Implement course registration with email notifications

### Asset Integration:
- Copy PNGs from `/PNGs` to `/app/static/images/`
- Set up background image on all pages
- Implement navigation with custom PNG buttons
- Add logo and favicon
- Create upload interface in admin for dynamic content
3. **Create detailed technical specifications**
4. **Set up initial project structure**
5. **Begin Phase 1 development**

---

## Notes

- **Ubuntu Server LTS 14:** This appears to be Ubuntu 14.04, which reached end-of-life in April 2019. Strong recommendation to upgrade to Ubuntu 22.04 LTS or 24.04 LTS for security and support.
- **WYSIWYG Focus:** The admin interface should feel like using a word processor or website builder, not a technical CMS.
- **Custom PNG Icons:** All navigation and buttons use custom graphics - ensure consistent design and proper sizing for responsive display.

