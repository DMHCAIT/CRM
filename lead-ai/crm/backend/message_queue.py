"""
Message Queue System
Reliable email and WhatsApp sending with retry logic and rate limiting
"""

from celery_config import celery_app
from database import SessionLocal, Lead as DBLead, User as DBUser, Activity as DBActivity
from datetime import datetime
from typing import List, Dict, Optional
from logger_config import logger
import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@crm.com')

# WhatsApp configuration
WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL', '')
WHATSAPP_API_KEY = os.getenv('WHATSAPP_API_KEY', '')

# ============================================================================
# EMAIL TASKS
# ============================================================================

@celery_app.task(
    bind=True,
    name='message_queue.send_email_task',
    max_retries=3,
    default_retry_delay=60  # Retry after 1 minute
)
def send_email_task(self, to_email: str, subject: str, body: str, from_email: Optional[str] = None):
    """
    Send email with retry logic
    
    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body (plain text or HTML)
        from_email: Sender email (optional)
    """
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email or FROM_EMAIL
        msg['To'] = to_email
        
        # Add body
        if '<html>' in body.lower():
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Send via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent to {to_email}: {subject}")
        
        return {
            'status': 'sent',
            'to': to_email,
            'subject': subject,
            'sent_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        
        # Retry logic
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for email to {to_email}")
            return {
                'status': 'failed',
                'to': to_email,
                'error': str(e)
            }


@celery_app.task(
    bind=True,
    name='message_queue.send_bulk_email',
    rate_limit='100/m'  # Max 100 emails per minute
)
def send_bulk_email(self, recipients: List[str], subject: str, body: str):
    """
    Send email to multiple recipients (queued)
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Email body
    """
    results = []
    total = len(recipients)
    
    for idx, email in enumerate(recipients):
        try:
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': idx + 1, 'total': total}
            )
            
            # Queue individual email
            result = send_email_task.delay(email, subject, body)
            results.append({
                'email': email,
                'task_id': result.id,
                'status': 'queued'
            })
            
        except Exception as e:
            logger.error(f"Failed to queue email for {email}: {e}")
            results.append({
                'email': email,
                'status': 'failed',
                'error': str(e)
            })
    
    return {
        'status': 'completed',
        'total': total,
        'queued': len([r for r in results if r['status'] == 'queued']),
        'failed': len([r for r in results if r['status'] == 'failed']),
        'results': results
    }


@celery_app.task(name='message_queue.send_lead_email')
def send_lead_email(lead_id: str, subject: str, body: str, user_id: int):
    """
    Send email to specific lead and log activity
    
    Args:
        lead_id: Lead ID
        subject: Email subject
        body: Email body
        user_id: User sending the email
    """
    db = SessionLocal()
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
        if not lead or not lead.email:
            return {'status': 'failed', 'error': 'Lead not found or no email'}
        
        # Send email
        result = send_email_task.delay(lead.email, subject, body)
        
        # Log activity
        activity = DBActivity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type='email_sent',
            description=f"Email sent: {subject}",
            metadata={
                'subject': subject,
                'task_id': result.id
            }
        )
        db.add(activity)
        
        # Update lead
        lead.last_contacted = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            'status': 'sent',
            'lead_id': lead_id,
            'task_id': result.id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send lead email: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# WHATSAPP TASKS
# ============================================================================

@celery_app.task(
    bind=True,
    name='message_queue.send_whatsapp_task',
    max_retries=3,
    default_retry_delay=60
)
def send_whatsapp_task(self, phone: str, message: str, template_id: Optional[str] = None):
    """
    Send WhatsApp message with retry logic
    
    Args:
        phone: Recipient phone number (with country code)
        message: Message text
        template_id: Optional template ID for business messages
    """
    try:
        # Format phone number (remove spaces, dashes)
        phone_clean = ''.join(filter(str.isdigit, phone))
        
        # Send via WhatsApp API (Meta Cloud API or Twilio)
        if WHATSAPP_API_URL and WHATSAPP_API_KEY:
            headers = {
                'Authorization': f'Bearer {WHATSAPP_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': phone_clean,
                'type': 'text',
                'text': {'body': message}
            }
            
            if template_id:
                payload['type'] = 'template'
                payload['template'] = {
                    'name': template_id,
                    'language': {'code': 'en'}
                }
            
            response = requests.post(
                WHATSAPP_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            
            logger.info(f"WhatsApp sent to {phone}: {message[:50]}...")
            
            return {
                'status': 'sent',
                'to': phone,
                'sent_at': datetime.utcnow().isoformat(),
                'response': response.json()
            }
        else:
            # Fallback: Log message (for testing without API)
            logger.warning(f"WhatsApp API not configured. Would send to {phone}: {message}")
            
            return {
                'status': 'simulated',
                'to': phone,
                'message': 'WhatsApp API not configured'
            }
            
    except requests.RequestException as e:
        logger.error(f"Failed to send WhatsApp to {phone}: {e}")
        
        # Retry logic
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for WhatsApp to {phone}")
            return {
                'status': 'failed',
                'to': phone,
                'error': str(e)
            }


@celery_app.task(
    bind=True,
    name='message_queue.send_bulk_whatsapp',
    rate_limit='50/m'  # Max 50 WhatsApp per minute
)
def send_bulk_whatsapp(self, recipients: List[Dict], message: str):
    """
    Send WhatsApp to multiple recipients
    
    Args:
        recipients: List of dicts with 'phone' and optionally 'name'
        message: Message text
    """
    results = []
    total = len(recipients)
    
    for idx, recipient in enumerate(recipients):
        try:
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': idx + 1, 'total': total}
            )
            
            phone = recipient.get('phone')
            if not phone:
                continue
            
            # Personalize message if name provided
            personalized_message = message
            if recipient.get('name'):
                personalized_message = message.replace('{{name}}', recipient['name'])
            
            # Queue WhatsApp
            result = send_whatsapp_task.delay(phone, personalized_message)
            results.append({
                'phone': phone,
                'task_id': result.id,
                'status': 'queued'
            })
            
        except Exception as e:
            logger.error(f"Failed to queue WhatsApp for {recipient.get('phone')}: {e}")
            results.append({
                'phone': recipient.get('phone'),
                'status': 'failed',
                'error': str(e)
            })
    
    return {
        'status': 'completed',
        'total': total,
        'queued': len([r for r in results if r['status'] == 'queued']),
        'failed': len([r for r in results if r['status'] == 'failed']),
        'results': results
    }


@celery_app.task(name='message_queue.send_lead_whatsapp')
def send_lead_whatsapp(lead_id: str, message: str, user_id: int, template_id: Optional[str] = None):
    """
    Send WhatsApp to specific lead and log activity
    
    Args:
        lead_id: Lead ID
        message: Message text
        user_id: User sending the message
        template_id: Optional template ID
    """
    db = SessionLocal()
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
        if not lead or not lead.phone:
            return {'status': 'failed', 'error': 'Lead not found or no phone'}
        
        # Send WhatsApp
        result = send_whatsapp_task.delay(lead.phone, message, template_id)
        
        # Log activity
        activity = DBActivity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type='whatsapp_sent',
            description=f"WhatsApp sent: {message[:50]}...",
            metadata={
                'message': message,
                'task_id': result.id,
                'template_id': template_id
            }
        )
        db.add(activity)
        
        # Update lead
        lead.last_contacted = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            'status': 'sent',
            'lead_id': lead_id,
            'task_id': result.id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send lead WhatsApp: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# TEMPLATE-BASED MESSAGING
# ============================================================================

@celery_app.task(name='message_queue.send_welcome_sequence')
def send_welcome_sequence(lead_id: str):
    """
    Send welcome message sequence to new lead
    (Email + WhatsApp)
    """
    db = SessionLocal()
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
        if not lead:
            return {'status': 'failed', 'error': 'Lead not found'}
        
        # Welcome email
        if lead.email:
            email_body = f"""
Dear {lead.name},

Welcome to [Your Company]! 🎓

Thank you for your interest in studying {lead.course_interested or 'abroad'}.

We're excited to help you achieve your educational goals. One of our counselors will contact you within 24 hours.

In the meantime, feel free to explore our website or reply to this email with any questions.

Best regards,
The Team
            """
            
            send_email_task.delay(
                to_email=lead.email,
                subject="Welcome! 🎓",
                body=email_body
            )
        
        # Welcome WhatsApp
        if lead.phone:
            whatsapp_msg = f"Hi {lead.name}! Welcome to [Your Company]. We received your inquiry about {lead.course_interested or 'studying abroad'}. Our counselor will contact you soon. Reply STOP to unsubscribe."
            
            send_whatsapp_task.delay(
                phone=lead.phone,
                message=whatsapp_msg
            )
        
        # Log activity
        activity = DBActivity(
            lead_id=lead.id,
            user_id=1,  # System user
            activity_type='welcome_sent',
            description="Welcome sequence sent (email + WhatsApp)"
        )
        db.add(activity)
        db.commit()
        
        return {
            'status': 'completed',
            'lead_id': lead_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send welcome sequence: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='message_queue.send_followup_sequence')
def send_followup_sequence(lead_id: str, sequence_type: str = 'standard'):
    """
    Send automated follow-up sequence
    
    Args:
        lead_id: Lead ID
        sequence_type: 'standard', 'hot', 'cold'
    """
    db = SessionLocal()
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
        if not lead:
            return {'status': 'failed', 'error': 'Lead not found'}
        
        # Different sequences based on type
        if sequence_type == 'hot':
            message = f"Hi {lead.name}, following up on your inquiry about {lead.course_interested}. Can we schedule a call today to discuss details? 📞"
        elif sequence_type == 'cold':
            message = f"Hi {lead.name}, just checking in! Are you still interested in {lead.course_interested}? Let us know if you have any questions. 😊"
        else:
            message = f"Hi {lead.name}, hope you're doing well! Wanted to follow up on your {lead.course_interested} application. Any questions we can help with?"
        
        # Send via preferred channel
        if lead.phone:
            send_whatsapp_task.delay(lead.phone, message)
        elif lead.email:
            send_email_task.delay(lead.email, "Following Up on Your Inquiry", message)
        
        # Log activity
        activity = DBActivity(
            lead_id=lead.id,
            user_id=1,
            activity_type='followup_sent',
            description=f"Automated follow-up sent ({sequence_type})"
        )
        db.add(activity)
        db.commit()
        
        return {
            'status': 'completed',
            'lead_id': lead_id,
            'sequence_type': sequence_type
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send follow-up sequence: {e}")
        raise
    finally:
        db.close()


print("✅ Message queue system loaded")
