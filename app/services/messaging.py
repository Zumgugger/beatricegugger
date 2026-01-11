"""Messaging service for SMS and Email."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import current_app, url_for
from flask_mail import Message
from app import db, mail
from app.models import MessageTemplate, MessageLog, ScheduledMessage, CourseRegistration, Course, SiteSettings

logger = logging.getLogger(__name__)


def is_sms_enabled():
    """Check if SMS is enabled (both config and runtime setting)."""
    # First check config - if disabled there, don't send
    if not current_app.config.get('SMS_ENABLED'):
        return False
    
    # Then check runtime setting from database
    setting = SiteSettings.query.filter_by(key='sms_enabled').first()
    if setting is not None:
        return setting.value == 'true'
    
    # Default to enabled if no runtime setting exists
    return True


def get_twilio_client():
    """Get Twilio client if configured."""
    if not is_sms_enabled():
        logger.info("SMS disabled via settings")
        return None
    
    account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
    auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
    
    if not account_sid or not auth_token:
        logger.warning("Twilio credentials not configured")
        return None
    
    try:
        from twilio.rest import Client
        return Client(account_sid, auth_token)
    except ImportError:
        logger.error("Twilio package not installed. Run: pip install twilio")
        return None
    except Exception as e:
        logger.error(f"Failed to create Twilio client: {e}")
        return None


def format_phone_for_twilio(phone: str) -> str:
    """Format phone number for Twilio (E.164 format)."""
    import re
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # If starts with 0, assume Swiss number
    if cleaned.startswith('0'):
        cleaned = '+41' + cleaned[1:]
    
    # If no +, add it
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    
    return cleaned


def get_template(message_type: str, trigger: str) -> Optional[MessageTemplate]:
    """Get message template by type and trigger."""
    return MessageTemplate.query.filter_by(
        message_type=message_type,
        trigger=trigger,
        is_active=True
    ).first()


def build_context(registration: CourseRegistration, **extra) -> Dict[str, Any]:
    """Build context dictionary for template rendering."""
    course = registration.course
    
    # Format date and time
    datum = course.date.strftime('%d.%m.%Y') if course.date else ''
    zeit = course.time_info or ''
    
    # Get location info
    ort = course.location or ''
    ort_url = course.location_url or ''
    
    # Build Google Maps URL if we have coordinates or address
    if ort_url:
        google_maps_link = ort_url
    elif ort:
        # Create Google Maps search URL
        import urllib.parse
        google_maps_link = f"https://maps.google.com/?q={urllib.parse.quote(ort)}"
    else:
        google_maps_link = ''
    
    context = {
        'vorname': registration.vorname,
        'name': registration.name,
        'telefonnummer': registration.telefonnummer,
        'email': registration.email or '',
        'kurstitel': course.title,
        'datum': datum,
        'zeit': zeit,
        'ort': ort,
        'ort_url': google_maps_link,
        'num_participants': registration.num_participants or 1,
    }
    
    # Add extra context
    context.update(extra)
    
    return context


def send_sms(
    recipient: str,
    body: str,
    registration_id: Optional[int] = None,
    course_id: Optional[int] = None,
    trigger: str = 'manual'
) -> bool:
    """Send SMS via Twilio."""
    client = get_twilio_client()
    
    if not client:
        logger.info(f"SMS not sent (disabled): {recipient[:6]}... - {body[:50]}...")
        # Log as pending/disabled
        log = MessageLog(
            message_type='sms',
            trigger=trigger,
            recipient=recipient,
            body=body,
            registration_id=registration_id,
            course_id=course_id,
            status='disabled',
            error_message='SMS not enabled'
        )
        db.session.add(log)
        db.session.commit()
        return False
    
    try:
        formatted_phone = format_phone_for_twilio(recipient)
        from_number = current_app.config.get('TWILIO_PHONE_NUMBER')
        
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=formatted_phone
        )
        
        # Log success
        log = MessageLog(
            message_type='sms',
            trigger=trigger,
            recipient=formatted_phone,
            body=body,
            registration_id=registration_id,
            course_id=course_id,
            status='sent',
            external_id=message.sid
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"SMS sent to {formatted_phone}: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {recipient}: {e}")
        
        # Log failure
        log = MessageLog(
            message_type='sms',
            trigger=trigger,
            recipient=recipient,
            body=body,
            registration_id=registration_id,
            course_id=course_id,
            status='failed',
            error_message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        
        return False


def send_email(
    recipient: str,
    subject: str,
    body: str,
    registration_id: Optional[int] = None,
    course_id: Optional[int] = None,
    trigger: str = 'manual'
) -> bool:
    """Send email via Flask-Mail."""
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body,
            reply_to=current_app.config.get('MAIL_REPLY_TO')
        )
        
        mail.send(msg)
        
        # Log success
        log = MessageLog(
            message_type='email',
            trigger=trigger,
            recipient=recipient,
            subject=subject,
            body=body,
            registration_id=registration_id,
            course_id=course_id,
            status='sent'
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Email sent to {recipient}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        
        # Log failure
        log = MessageLog(
            message_type='email',
            trigger=trigger,
            recipient=recipient,
            subject=subject,
            body=body,
            registration_id=registration_id,
            course_id=course_id,
            status='failed',
            error_message=str(e)
        )
        db.session.add(log)
        db.session.commit()
        
        return False


def send_registration_messages(
    registration: CourseRegistration,
    status: str,  # 'confirmed', 'waitlist', 'mixed'
    num_registered: int = 0,
    num_waitlist: int = 0
):
    """Send SMS and email for registration.
    
    Args:
        registration: The registration object
        status: 'confirmed', 'waitlist', or 'mixed'
        num_registered: Number of participants registered (for mixed)
        num_waitlist: Number of participants on waitlist (for mixed)
    """
    course = registration.course
    
    # Determine trigger based on status
    if status == 'confirmed':
        trigger = 'registration_confirmed'
    elif status == 'waitlist':
        trigger = 'registration_waitlist'
    elif status == 'mixed':
        trigger = 'registration_mixed'
    else:
        logger.error(f"Unknown registration status: {status}")
        return
    
    # Build context
    context = build_context(registration)
    context['num_registered'] = num_registered
    context['num_waitlist'] = num_waitlist
    
    # Send SMS
    sms_template = get_template('sms', trigger)
    if sms_template:
        body = sms_template.render(**context)
        send_sms(
            recipient=registration.telefonnummer,
            body=body,
            registration_id=registration.id,
            course_id=course.id,
            trigger=trigger
        )
    else:
        logger.warning(f"No SMS template found for trigger: {trigger}")
    
    # Send Email (if email provided)
    if registration.email:
        email_template = get_template('email', trigger)
        if email_template:
            subject = email_template.render_subject(**context)
            body = email_template.render(**context)
            send_email(
                recipient=registration.email,
                subject=subject,
                body=body,
                registration_id=registration.id,
                course_id=course.id,
                trigger=trigger
            )
    
    # Schedule reminder SMS (only for confirmed registrations)
    if status in ('confirmed', 'mixed') and not registration.is_waitlist:
        schedule_reminder_sms(registration)
    
    # Send admin notification SMS
    send_admin_notification(registration)


def send_admin_notification(registration: CourseRegistration):
    """Send SMS notification to admin when someone registers."""
    trigger = 'admin_new_registration'
    admin_phone = current_app.config.get('ADMIN_PHONE', '+41797134974')
    
    # Get template
    sms_template = get_template('sms', trigger)
    if not sms_template:
        logger.warning(f"No SMS template found for trigger: {trigger}")
        return
    
    # Build context
    context = build_context(registration)
    body = sms_template.render(**context)
    
    # Send SMS to admin
    send_sms(
        recipient=admin_phone,
        body=body,
        registration_id=registration.id,
        course_id=registration.course_id,
        trigger=trigger
    )


def send_promoted_message(registration: CourseRegistration):
    """Send SMS when someone is promoted from waitlist to registered."""
    trigger = 'promoted_from_waitlist'
    context = build_context(registration)
    
    # Send SMS
    sms_template = get_template('sms', trigger)
    if sms_template:
        body = sms_template.render(**context)
        send_sms(
            recipient=registration.telefonnummer,
            body=body,
            registration_id=registration.id,
            course_id=registration.course_id,
            trigger=trigger
        )
    
    # Send Email
    if registration.email:
        email_template = get_template('email', trigger)
        if email_template:
            subject = email_template.render_subject(**context)
            body = email_template.render(**context)
            send_email(
                recipient=registration.email,
                subject=subject,
                body=body,
                registration_id=registration.id,
                course_id=registration.course_id,
                trigger=trigger
            )
    
    # Schedule reminder SMS
    schedule_reminder_sms(registration)


def schedule_reminder_sms(registration: CourseRegistration):
    """Schedule reminder SMS for 1 day before course.
    
    Only schedules if:
    - Course date is more than 2 days away (otherwise only initial SMS)
    - Registration is not on waitlist
    """
    course = registration.course
    
    if not course.date:
        logger.warning(f"Cannot schedule reminder: Course {course.id} has no date")
        return
    
    if registration.is_waitlist:
        logger.info(f"Not scheduling reminder for waitlist registration {registration.id}")
        return
    
    # Calculate time until course
    now = datetime.utcnow()
    course_datetime = datetime.combine(course.date, datetime.min.time())
    
    # If course has time_info, try to parse it for more accurate scheduling
    # For now, assume course starts at 9:00 AM
    course_datetime = course_datetime.replace(hour=9, minute=0)
    
    days_until_course = (course_datetime - now).days
    
    if days_until_course < 2:
        logger.info(f"Course too soon ({days_until_course} days), not scheduling reminder")
        return
    
    # Schedule for 1 day before at 10:00 AM
    reminder_time = course_datetime - timedelta(days=1)
    reminder_time = reminder_time.replace(hour=10, minute=0, second=0, microsecond=0)
    
    # Check if already scheduled
    existing = ScheduledMessage.query.filter_by(
        registration_id=registration.id,
        trigger='reminder_1day',
        status='pending'
    ).first()
    
    if existing:
        logger.info(f"Reminder already scheduled for registration {registration.id}")
        return
    
    # Create scheduled message
    scheduled = ScheduledMessage(
        message_type='sms',
        trigger='reminder_1day',
        recipient=registration.telefonnummer,
        registration_id=registration.id,
        course_id=course.id,
        scheduled_for=reminder_time,
        status='pending'
    )
    db.session.add(scheduled)
    db.session.commit()
    
    logger.info(f"Scheduled reminder for {registration.id} at {reminder_time}")


def process_scheduled_messages():
    """Process all pending scheduled messages that are due.
    
    This should be called periodically (e.g., by a cron job or scheduler).
    """
    now = datetime.utcnow()
    
    pending = ScheduledMessage.query.filter(
        ScheduledMessage.status == 'pending',
        ScheduledMessage.scheduled_for <= now
    ).all()
    
    for scheduled in pending:
        # Get template
        template = get_template(scheduled.message_type, scheduled.trigger)
        
        if not template:
            logger.error(f"No template for scheduled message {scheduled.id}")
            scheduled.status = 'failed'
            scheduled.error_message = 'Template not found'
            continue
        
        # Get registration and build context
        registration = scheduled.registration
        if not registration:
            scheduled.status = 'failed'
            scheduled.error_message = 'Registration not found'
            continue
        
        context = build_context(registration)
        body = template.render(**context)
        
        # Send message
        if scheduled.message_type == 'sms':
            success = send_sms(
                recipient=scheduled.recipient,
                body=body,
                registration_id=scheduled.registration_id,
                course_id=scheduled.course_id,
                trigger=scheduled.trigger
            )
        else:
            subject = template.render_subject(**context)
            success = send_email(
                recipient=scheduled.recipient,
                subject=subject,
                body=body,
                registration_id=scheduled.registration_id,
                course_id=scheduled.course_id,
                trigger=scheduled.trigger
            )
        
        # Update status
        scheduled.status = 'sent' if success else 'failed'
        scheduled.sent_at = now
    
    db.session.commit()
    
    return len(pending)


def cancel_scheduled_messages(registration_id: int):
    """Cancel all pending scheduled messages for a registration."""
    ScheduledMessage.query.filter_by(
        registration_id=registration_id,
        status='pending'
    ).update({'status': 'cancelled'})
    db.session.commit()


def init_default_templates():
    """Initialize default message templates if not exist."""
    templates = [
        # SMS Templates
        {
            'message_type': 'sms',
            'trigger': 'registration_confirmed',
            'body': 'Danke {vorname} für deine Anmeldung für den Kurs {kurstitel}. Ich freue mich auf dich. Der Kurs findet statt in {ort} am {datum} um {zeit}. Bezahlen kannst du vor Ort oder nach dem Kurs per Rechnung.'
        },
        {
            'message_type': 'sms',
            'trigger': 'registration_mixed',
            'body': 'Danke {vorname} für deine Anmeldung für den Kurs {kurstitel}. Ich freue mich auf dich. Der Kurs findet statt in {ort} am {datum} um {zeit}. Bezahlen kannst du vor Ort oder nach dem Kurs per Rechnung. {num_registered} Personen sind angemeldet für den Kurs, {num_waitlist} sind leider noch auf der Warteliste. Ich kontaktiere dich, sobald Plätze frei werden.'
        },
        {
            'message_type': 'sms',
            'trigger': 'registration_waitlist',
            'body': 'Danke {vorname} für deine Anmeldung für den Kurs {kurstitel}. Leider bist du noch auf der Warteliste. Ich kontaktiere dich, sobald Plätze frei werden.'
        },
        {
            'message_type': 'sms',
            'trigger': 'promoted_from_waitlist',
            'body': 'Ein Platz im Kurs {kurstitel} wurde frei. Der Kurs findet statt in {ort} am {datum} um {zeit}. Du bist jetzt angemeldet. Bezahlen kannst du vor Ort oder nach dem Kurs per Rechnung.'
        },
        {
            'message_type': 'sms',
            'trigger': 'reminder_1day',
            'body': 'Juhu, morgen um {zeit} findet der Kurs {kurstitel} statt. {ort_url}'
        },
        {
            'message_type': 'sms',
            'trigger': 'admin_new_registration',
            'body': '{num_participants} Person(en) hat/haben sich für den {kurstitel} vom {datum} angemeldet.'
        },
        
        # Email Templates
        {
            'message_type': 'email',
            'trigger': 'registration_confirmed',
            'subject': 'Anmeldung bestätigt: {kurstitel}',
            'body': '''Hallo {vorname},

Danke für deine Anmeldung für den Kurs "{kurstitel}".

📅 Datum: {datum}
⏰ Zeit: {zeit}
📍 Ort: {ort}

Bezahlen kannst du vor Ort oder nach dem Kurs per Rechnung.

Ich freue mich auf dich!

Herzliche Grüsse,
Beatrice Gugger'''
        },
        {
            'message_type': 'email',
            'trigger': 'registration_mixed',
            'subject': 'Anmeldung: {kurstitel}',
            'body': '''Hallo {vorname},

Danke für deine Anmeldung für den Kurs "{kurstitel}".

📅 Datum: {datum}
⏰ Zeit: {zeit}
📍 Ort: {ort}

{num_registered} Person(en) sind angemeldet für den Kurs.
{num_waitlist} Person(en) sind leider noch auf der Warteliste.

Ich kontaktiere dich, sobald Plätze frei werden.

Bezahlen kannst du vor Ort oder nach dem Kurs per Rechnung.

Herzliche Grüsse,
Beatrice Gugger'''
        },
        {
            'message_type': 'email',
            'trigger': 'registration_waitlist',
            'subject': 'Warteliste: {kurstitel}',
            'body': '''Hallo {vorname},

Danke für deine Anmeldung für den Kurs "{kurstitel}".

Leider ist der Kurs momentan ausgebucht und du bist auf der Warteliste.
Ich kontaktiere dich, sobald ein Platz frei wird.

Herzliche Grüsse,
Beatrice Gugger'''
        },
        {
            'message_type': 'email',
            'trigger': 'promoted_from_waitlist',
            'subject': 'Platz frei: {kurstitel}',
            'body': '''Hallo {vorname},

Gute Neuigkeiten! Ein Platz im Kurs "{kurstitel}" ist frei geworden.

📅 Datum: {datum}
⏰ Zeit: {zeit}
📍 Ort: {ort}

Du bist jetzt angemeldet. Bezahlen kannst du vor Ort oder nach dem Kurs per Rechnung.

Ich freue mich auf dich!

Herzliche Grüsse,
Beatrice Gugger'''
        },
    ]
    
    for tpl in templates:
        existing = MessageTemplate.query.filter_by(
            message_type=tpl['message_type'],
            trigger=tpl['trigger']
        ).first()
        
        if not existing:
            template = MessageTemplate(**tpl)
            db.session.add(template)
    
    db.session.commit()
