# Optimized Project Plan - Lessons Learned

**Based on:** Beatrice Gugger Website Development  
**Purpose:** Reference for future Flask projects to avoid common pitfalls

---

## 1. Pre-Development Checklist

### 1.1 Feature Requirements - Ask These FIRST

Before writing any code, get clear answers on:

```markdown
□ Registration/Booking System:
  - Can one person register multiple participants? (num_participants from day 1)
  - Is there a waitlist when full? (is_waitlist from day 1)
  - What fields are required? (define ALL fields upfront)
  
□ Capacity Management:
  - How should "spots" be counted? (entries vs participants)
  - What happens when course is full? (disable, waitlist, overflow?)
  - Can admin override capacity limits?

□ User Roles:
  - How many admin users? (plan for multi-admin from start)
  - Can admins delete themselves? (add safety checks)
  - Password requirements? (min length, complexity)

□ Notifications:
  - What triggers emails? (registration, waitlist, cancellation)
  - Different messages for different states? (confirmed vs waitlist)
  - Admin notifications needed?
```

### 1.2 Database Schema - Plan for Future

**Golden Rule:** Add fields you MIGHT need with sensible defaults.

```python
# BAD: Minimal model that needs migration later
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    # Later: "Oh we need waitlist!" → Migration headache

# GOOD: Future-proof model from day 1
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Capacity management (even if not used initially)
    num_participants = db.Column(db.Integer, default=1, nullable=False)
    is_waitlist = db.Column(db.Boolean, default=False, nullable=False)
    
    # Status tracking (plan for cancellations)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, waitlist, cancelled
    
    # Audit fields (always useful)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 1.3 Counting Logic - Decide Early

**Problem we had:** Started counting registration ENTRIES, later needed to count PARTICIPANTS.

```python
# Define clearly in models.py from the start:

@property
def registration_count(self):
    """Count PARTICIPANTS (sum of num_participants), not entries."""
    from sqlalchemy import func
    result = db.session.query(func.sum(Registration.num_participants)).filter(
        Registration.course_id == self.id,
        Registration.is_waitlist == False
    ).scalar()
    return result or 0  # Always handle NULL!

@property
def spots_available(self):
    """Available spots = max - registered participants."""
    if self.max_participants:
        return max(0, self.max_participants - self.registration_count)
    return None  # Unlimited
```

---

## 2. Flask Application Structure

### 2.1 Rate Limiting - Exempt Static Resources

**Problem we had:** Global rate limits blocked image loading (429 errors).

```python
# In app/__init__.py

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Use reasonable defaults (not too restrictive for browsing)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"]  # Not 50/hour!
)

def create_app():
    app = Flask(__name__)
    limiter.init_app(app)
    
    # ALWAYS exempt static file routes
    @app.route('/uploads/<path:filename>')
    @limiter.exempt  # ← Critical!
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    @app.route('/health')
    @limiter.exempt
    def health_check():
        return jsonify({'status': 'healthy'})
```

### 2.2 Template Helpers - Handle Edge Cases

**Problem we had:** NULL values in Jinja templates caused crashes.

```python
# Create template utilities in app/utils/template_helpers.py

def safe_int(value, default=0):
    """Safely convert to int, handling None."""
    return int(value) if value is not None else default

def plural_de(count, singular, plural):
    """German singular/plural helper."""
    return singular if count == 1 else plural

# Register in app factory:
@app.context_processor
def utility_processor():
    return {
        'safe_int': safe_int,
        'plural_de': plural_de
    }
```

```html
<!-- In templates - clean and safe -->
{{ count }} {{ plural_de(count, 'Platz', 'Plätze') }} frei

<!-- Instead of error-prone: -->
{{ count }} Platz{% if count != 1 %}e{% endif %} frei
```

### 2.3 Template NULL Safety

**Problem we had:** `{% if reg.num_participants > 1 %}` crashed on NULL.

```html
<!-- BAD: Crashes if num_participants is NULL -->
{% if reg.num_participants > 1 %}

<!-- GOOD: Safe with default -->
{% if (reg.num_participants or 1) > 1 %}

<!-- BETTER: Use model property that never returns NULL -->
{% if reg.participant_count > 1 %}
```

---

## 3. Database Migration Strategy

### 3.1 Migration Checklist

When adding new fields to existing tables:

```bash
# 1. Add field with DEFAULT and nullable=False (or handle NULLs)
num_participants = db.Column(db.Integer, default=1, nullable=False)

# 2. Create migration
flask db migrate -m "Add num_participants to Registration"

# 3. BEFORE upgrading, check the migration file!
# Edit migrations/versions/xxx.py if needed:

def upgrade():
    # Add column with server_default for existing rows
    op.add_column('registrations', 
        sa.Column('num_participants', sa.Integer(), 
                  nullable=False, server_default='1'))

# 4. Apply migration
flask db upgrade

# 5. If you forgot server_default, fix existing data:
sqlite3 database.db "UPDATE registrations SET num_participants = 1 WHERE num_participants IS NULL;"
```

### 3.2 Safe Field Addition Pattern

```python
# In migration file - always provide server_default for new NOT NULL columns

def upgrade():
    # Step 1: Add as nullable with default
    op.add_column('table_name',
        sa.Column('new_field', sa.Integer(), nullable=True, server_default='1'))
    
    # Step 2: Update any NULL values (belt and suspenders)
    op.execute("UPDATE table_name SET new_field = 1 WHERE new_field IS NULL")
    
    # Step 3: Make non-nullable if needed
    op.alter_column('table_name', 'new_field', nullable=False)
```

---

## 4. UI/UX Patterns

### 4.1 Status Display - Plan All States

**Problem we had:** Added waitlist later, had to change disabled button to link.

```html
<!-- Plan all states from the beginning -->
<div class="course-actions">
    {% if course.status == 'open' %}
        <a href="{{ url_for('register') }}" class="btn btn-primary">Anmelden</a>
    {% elif course.status == 'waitlist_available' %}
        <a href="{{ url_for('register') }}" class="btn btn-waitlist">Warteliste</a>
    {% elif course.status == 'closed' %}
        <span class="btn btn-disabled">Geschlossen</span>
    {% endif %}
</div>
```

### 4.2 CSS - Avoid State-Based Dimming

**Problem we had:** Grey/dimmed styling for "full" courses conflicted with waitlist.

```css
/* BAD: Styling based on availability state */
.course-item.course-full {
    opacity: 0.7;  /* Makes waitlist button look disabled */
    border-left-color: #999;
}

/* GOOD: Use badges/labels for status, keep cards consistent */
.course-item {
    /* Same styling regardless of status */
    border-left: 4px solid #8B4513;
}

.status-badge.full {
    background: #dc3545;
    color: white;
}

.status-badge.waitlist {
    background: #ffc107;
    color: black;
}
```

### 4.3 Admin Actions - Safety Checks

```html
<!-- Always prevent self-destructive actions -->
<div class="user-actions">
    <button onclick="editUser({{ user.id }})">✏️</button>
    
    {% if user.id != current_user.id %}
        <button onclick="deleteUser({{ user.id }})">🗑️</button>
    {% endif %}
    <!-- No delete button for yourself -->
</div>
```

---

## 5. API Design Patterns

### 5.1 Consistent Response Format

```python
# Always return consistent JSON structure

# Success
return jsonify({
    'success': True,
    'data': {...},
    'message': 'Operation completed'
})

# Error
return jsonify({
    'success': False,
    'error': 'Specific error message'
}), 400  # Always include status code
```

### 5.2 Validation Helpers

```python
# Create reusable validators in app/utils/validators.py

import re

def validate_phone(phone: str) -> bool:
    """Swiss/international phone validation."""
    if not phone:
        return False
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+?\d{9,15}$', cleaned))

def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return True  # Optional field
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email))

# Use consistently in all routes
```

---

## 6. Development Workflow

### 6.1 Feature Implementation Order

```markdown
1. **Database Model** - Define with all future fields
2. **Migration** - Create and verify before running
3. **Model Properties** - Add computed properties (counts, status)
4. **API Routes** - CRUD operations with validation
5. **Templates** - With NULL safety and plural handling
6. **CSS** - Status-agnostic base styling
7. **JavaScript** - API calls with error handling
8. **Tests** - Cover edge cases (NULL, empty, full)
```

### 6.2 Commit Strategy

```bash
# Atomic commits with clear scope
git commit -m "Add Registration model with num_participants, is_waitlist fields"
git commit -m "Add registration count property (sum participants, not entries)"
git commit -m "Add waitlist registration flow with success templates"
git commit -m "Add promote-from-waitlist admin action"

# NOT: "Add waitlist feature" (too broad, hard to revert partially)
```

### 6.3 Testing Checklist Per Feature

```markdown
□ Happy path works
□ NULL/empty values handled
□ Edge cases (0, 1, max values)
□ Singular/plural text correct
□ Admin can't break things (self-delete, etc.)
□ Rate limits don't block legitimate use
□ Mobile responsive
```

---

## 7. Quick Reference - Common Fixes

| Problem | Solution |
|---------|----------|
| NULL comparison in Jinja | `(value or default)` |
| 429 on images | `@limiter.exempt` on upload routes |
| Migration fails on NOT NULL | Add `server_default` |
| Count entries vs participants | Use `func.sum()` not `func.count()` |
| Singular/plural German | Create `plural_de()` helper |
| Self-deletion | Check `user.id != current_user.id` |
| Disabled button should be link | Plan all states upfront |

---

## 8. Project Kickoff Template

```markdown
# New Project Checklist

## Before Coding
- [ ] List ALL user actions (register, cancel, edit, delete...)
- [ ] Define ALL statuses (open, full, waitlist, cancelled...)
- [ ] Identify counting needs (entries vs quantities)
- [ ] Plan admin safety (what can't they do to themselves?)
- [ ] Define notification triggers

## Database Design
- [ ] Add audit fields (created_at, updated_at)
- [ ] Add status/flag fields even if not used yet
- [ ] Use defaults and non-nullable where possible
- [ ] Plan for soft-delete if needed

## Flask Setup
- [ ] Exempt static routes from rate limiting
- [ ] Create template helpers for NULL safety
- [ ] Create validation helpers
- [ ] Set up consistent API response format

## Templates
- [ ] Use plural helpers, not inline conditionals
- [ ] Always use `(value or default)` for comparisons
- [ ] Plan all UI states before implementing
```

---

## 9. Summary of Key Lessons

1. **Ask about multi-quantity early** - "Can one registration have multiple participants?"
2. **Plan for waitlist from day 1** - Even if client says "not needed yet"
3. **Sum, don't count** - When tracking capacity with quantities
4. **Exempt static routes** - Rate limiting kills image-heavy pages
5. **NULL-safe templates** - Always use `(value or default)`
6. **Consistent pluralization** - Use helpers, not inline logic
7. **Style states with badges** - Not by dimming entire components
8. **Prevent self-harm** - Admins can't delete themselves
9. **Atomic migrations** - One field at a time, with defaults
10. **Test edge cases** - 0, 1, NULL, max values

---

*Document created: January 10, 2026*  
*Based on real issues encountered during development*
