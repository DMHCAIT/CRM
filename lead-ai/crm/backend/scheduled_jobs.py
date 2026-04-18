"""
Scheduled Jobs - Periodic Tasks
Runs automated workflows on schedule (hourly, daily, weekly)
"""

from celery_config import celery_app
from database import SessionLocal, Lead as DBLead, User as DBUser, Activity as DBActivity
from datetime import datetime, timedelta
from typing import List, Dict
from logger_config import logger
import requests
import json

# ============================================================================
# LEAD MANAGEMENT JOBS
# ============================================================================

@celery_app.task(name='scheduled_jobs.update_all_lead_scores')
def update_all_lead_scores():
    """
    Daily job: Update AI scores for all active leads
    Runs at 2 AM every day
    """
    from background_tasks import ai_score_bulk_leads
    
    db = SessionLocal()
    try:
        # Get all active leads
        active_leads = db.query(DBLead).filter(
            DBLead.status.in_(['new', 'contacted', 'qualified', 'warm', 'hot'])
        ).all()
        
        lead_ids = [lead.lead_id for lead in active_leads]
        
        # Trigger bulk scoring task
        if lead_ids:
            result = ai_score_bulk_leads.delay(lead_ids)
            logger.info(f"Triggered AI scoring for {len(lead_ids)} leads. Task ID: {result.id}")
        
        return {
            'status': 'scheduled',
            'leads_count': len(lead_ids)
        }
        
    finally:
        db.close()


@celery_app.task(name='scheduled_jobs.auto_assign_unassigned_leads')
def auto_assign_unassigned_leads():
    """
    Auto-assign new unassigned leads every 2 hours during work hours
    """
    from auto_assignment_orchestrator import AutoAssignmentOrchestrator
    
    db = SessionLocal()
    try:
        # Get unassigned leads created in last 2 hours
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        
        unassigned = db.query(DBLead).filter(
            DBLead.assigned_to.is_(None),
            DBLead.created_at >= two_hours_ago,
            DBLead.status.in_(['new', 'contacted'])
        ).all()
        
        orchestrator = AutoAssignmentOrchestrator(db)
        assigned_count = 0
        
        for lead in unassigned:
            try:
                # Use intelligent strategy
                result = orchestrator.assign_lead(
                    lead_id=lead.id,
                    strategy='intelligent',
                    hospital_id=lead.hospital_id
                )
                
                if result['success']:
                    assigned_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to auto-assign lead {lead.lead_id}: {e}")
                continue
        
        db.commit()
        
        logger.info(f"Auto-assigned {assigned_count} new leads")
        
        return {
            'status': 'completed',
            'assigned': assigned_count,
            'total': len(unassigned)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Auto-assign job failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='scheduled_jobs.trigger_stale_lead_workflow')
def trigger_stale_lead_workflow():
    """
    Re-engage leads with no activity in 7+ days
    Runs daily at 10 AM
    """
    from workflow_engine import WorkflowEngine
    
    db = SessionLocal()
    try:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Find stale leads
        stale_leads = db.query(DBLead).filter(
            DBLead.updated_at < seven_days_ago,
            DBLead.status.in_(['warm', 'qualified', 'contacted']),
            DBLead.ai_score >= 50  # Only high-value leads
        ).all()
        
        engine = WorkflowEngine(db)
        triggered_count = 0
        
        for lead in stale_leads:
            try:
                # Trigger stale lead workflow
                engine.trigger_custom_event(
                    event_type='lead_inactive',
                    lead_id=lead.id,
                    user_id=lead.assigned_to or 1,
                    metadata={'days_inactive': 7}
                )
                triggered_count += 1
                
            except Exception as e:
                logger.error(f"Failed to trigger workflow for {lead.lead_id}: {e}")
                continue
        
        logger.info(f"Triggered re-engagement for {triggered_count} stale leads")
        
        return {
            'status': 'completed',
            'triggered': triggered_count
        }
        
    finally:
        db.close()


# ============================================================================
# ALERT & NOTIFICATION JOBS
# ============================================================================

@celery_app.task(name='scheduled_jobs.send_overdue_followup_alerts')
def send_overdue_followup_alerts():
    """
    Send alerts for overdue follow-ups
    Runs every hour
    """
    from message_queue import send_email_task
    
    db = SessionLocal()
    try:
        # Find overdue follow-ups
        now = datetime.utcnow()
        
        overdue_leads = db.query(DBLead).filter(
            DBLead.next_follow_up < now,
            DBLead.status.in_(['contacted', 'qualified', 'warm', 'hot']),
            DBLead.assigned_to.isnot(None)
        ).all()
        
        # Group by counselor
        counselor_overdues = {}
        for lead in overdue_leads:
            counselor_id = lead.assigned_to
            if counselor_id not in counselor_overdues:
                counselor_overdues[counselor_id] = []
            counselor_overdues[counselor_id].append(lead)
        
        # Send alerts
        sent_count = 0
        for counselor_id, leads in counselor_overdues.items():
            try:
                counselor = db.query(DBUser).filter(DBUser.id == counselor_id).first()
                if counselor and counselor.email:
                    # Send email alert
                    send_email_task.delay(
                        to_email=counselor.email,
                        subject=f"⏰ {len(leads)} Overdue Follow-ups",
                        body=format_overdue_alert(counselor.name, leads)
                    )
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send alert to counselor {counselor_id}: {e}")
                continue
        
        logger.info(f"Sent {sent_count} overdue follow-up alerts")
        
        return {
            'status': 'completed',
            'alerts_sent': sent_count,
            'overdue_count': len(overdue_leads)
        }
        
    finally:
        db.close()


@celery_app.task(name='scheduled_jobs.send_followup_reminders')
def send_followup_reminders():
    """
    Send reminders for upcoming follow-ups (next 2 hours)
    Runs every 2 hours during work hours
    """
    from message_queue import send_email_task
    
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        two_hours_later = now + timedelta(hours=2)
        
        upcoming_followups = db.query(DBLead).filter(
            DBLead.next_follow_up >= now,
            DBLead.next_follow_up <= two_hours_later,
            DBLead.assigned_to.isnot(None)
        ).all()
        
        # Group by counselor
        counselor_reminders = {}
        for lead in upcoming_followups:
            counselor_id = lead.assigned_to
            if counselor_id not in counselor_reminders:
                counselor_reminders[counselor_id] = []
            counselor_reminders[counselor_id].append(lead)
        
        sent_count = 0
        for counselor_id, leads in counselor_reminders.items():
            try:
                counselor = db.query(DBUser).filter(DBUser.id == counselor_id).first()
                if counselor and counselor.email:
                    send_email_task.delay(
                        to_email=counselor.email,
                        subject=f"📅 {len(leads)} Follow-ups in Next 2 Hours",
                        body=format_reminder_email(counselor.name, leads)
                    )
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send reminder to counselor {counselor_id}: {e}")
                continue
        
        logger.info(f"Sent {sent_count} follow-up reminders")
        
        return {
            'status': 'completed',
            'reminders_sent': sent_count
        }
        
    finally:
        db.close()


# ============================================================================
# REPORTING JOBS
# ============================================================================

@celery_app.task(name='scheduled_jobs.send_daily_performance_report')
def send_daily_performance_report():
    """
    Send daily performance summary to all counselors
    Runs every day at 8 AM
    """
    from message_queue import send_email_task
    
    db = SessionLocal()
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        today = datetime.utcnow()
        
        # Get all counselors
        counselors = db.query(DBUser).filter(
            DBUser.role.in_(['Counselor', 'Team Leader'])
        ).all()
        
        sent_count = 0
        
        for counselor in counselors:
            try:
                # Calculate yesterday's stats
                activities = db.query(DBActivity).filter(
                    DBActivity.user_id == counselor.id,
                    DBActivity.created_at >= yesterday,
                    DBActivity.created_at < today
                ).all()
                
                calls_made = len([a for a in activities if a.activity_type in ['call', 'contacted']])
                emails_sent = len([a for a in activities if a.activity_type == 'email_sent'])
                whatsapp_sent = len([a for a in activities if a.activity_type == 'whatsapp_sent'])
                
                # Get assigned leads
                assigned_leads = db.query(DBLead).filter(
                    DBLead.assigned_to == counselor.id
                ).all()
                
                hot_leads = len([l for l in assigned_leads if l.ai_segment == 'Hot'])
                today_followups = len([l for l in assigned_leads if l.next_follow_up and 
                                      l.next_follow_up.date() == today.date()])
                
                # Send report
                report_body = f"""
Good Morning {counselor.name}! 📊

Here's your daily performance summary:

**Yesterday's Activity:**
- 📞 Calls Made: {calls_made}
- ✉️ Emails Sent: {emails_sent}
- 💬 WhatsApp Messages: {whatsapp_sent}

**Current Pipeline:**
- 🔥 Hot Leads: {hot_leads}
- 📅 Today's Follow-ups: {today_followups}
- 📋 Total Assigned: {len(assigned_leads)}

Keep up the great work! 🚀
                """
                
                send_email_task.delay(
                    to_email=counselor.email,
                    subject=f"📊 Daily Performance Report - {today.strftime('%B %d, %Y')}",
                    body=report_body
                )
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send report to {counselor.email}: {e}")
                continue
        
        logger.info(f"Sent daily reports to {sent_count} counselors")
        
        return {
            'status': 'completed',
            'reports_sent': sent_count
        }
        
    finally:
        db.close()


@celery_app.task(name='scheduled_jobs.send_weekly_summary_report')
def send_weekly_summary_report():
    """
    Send weekly summary to managers and admins
    Runs every Monday at 9 AM
    """
    from message_queue import send_email_task
    
    db = SessionLocal()
    try:
        last_week = datetime.utcnow() - timedelta(days=7)
        
        # Get managers and admins
        recipients = db.query(DBUser).filter(
            DBUser.role.in_(['Manager', 'Hospital Admin', 'Super Admin'])
        ).all()
        
        # Calculate weekly stats
        new_leads = db.query(DBLead).filter(
            DBLead.created_at >= last_week
        ).count()
        
        enrolled = db.query(DBLead).filter(
            DBLead.status == 'enrolled',
            DBLead.updated_at >= last_week
        ).count()
        
        total_activities = db.query(DBActivity).filter(
            DBActivity.created_at >= last_week
        ).count()
        
        # Top performers
        counselors_stats = {}
        activities = db.query(DBActivity).filter(
            DBActivity.created_at >= last_week
        ).all()
        
        for activity in activities:
            user_id = activity.user_id
            if user_id not in counselors_stats:
                counselors_stats[user_id] = 0
            counselors_stats[user_id] += 1
        
        top_performers = sorted(counselors_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Format report
        report_body = f"""
Weekly Summary Report 📈
{last_week.strftime('%B %d')} - {datetime.utcnow().strftime('%B %d, %Y')}

**Key Metrics:**
- 🆕 New Leads: {new_leads}
- 🎓 Enrollments: {enrolled}
- 📊 Total Activities: {total_activities}

**Top Performers:**
"""
        
        for idx, (user_id, count) in enumerate(top_performers, 1):
            user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if user:
                report_body += f"{idx}. {user.name} - {count} activities\n"
        
        # Send to all recipients
        sent_count = 0
        for recipient in recipients:
            try:
                send_email_task.delay(
                    to_email=recipient.email,
                    subject="📈 Weekly CRM Summary Report",
                    body=report_body
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send weekly report to {recipient.email}: {e}")
                continue
        
        logger.info(f"Sent weekly reports to {sent_count} recipients")
        
        return {
            'status': 'completed',
            'reports_sent': sent_count
        }
        
    finally:
        db.close()


# ============================================================================
# DATA SYNC JOBS
# ============================================================================

@celery_app.task(name='scheduled_jobs.sync_google_sheets_data')
def sync_google_sheets_data():
    """
    Sync data with Google Sheets
    Runs every 30 minutes
    """
    # This would call your existing Google Sheets sync logic
    logger.info("Google Sheets sync started")
    
    # Placeholder - implement actual sync logic
    return {
        'status': 'completed',
        'synced': 0
    }


# ============================================================================
# MAINTENANCE JOBS
# ============================================================================

@celery_app.task(name='scheduled_jobs.cleanup_old_activities')
def cleanup_old_activities():
    """
    Archive activities older than 90 days
    Runs daily at 3 AM
    """
    db = SessionLocal()
    try:
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        
        old_activities = db.query(DBActivity).filter(
            DBActivity.created_at < ninety_days_ago
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {old_activities} old activities")
        
        return {
            'status': 'completed',
            'cleaned': old_activities
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Cleanup failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name='scheduled_jobs.warm_application_cache')
def warm_application_cache():
    """
    Pre-load frequently accessed data into cache
    Runs daily at 1 AM
    """
    from cache import warm_cache
    
    try:
        warm_cache()
        logger.info("Cache warmed successfully")
        
        return {'status': 'completed'}
        
    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")
        raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_overdue_alert(counselor_name: str, leads: List) -> str:
    """Format overdue follow-up alert email"""
    body = f"""
Hi {counselor_name},

You have {len(leads)} overdue follow-ups that need attention:

"""
    for lead in leads[:10]:  # Show first 10
        hours_overdue = (datetime.utcnow() - lead.next_follow_up).total_seconds() / 3600
        body += f"- {lead.name} ({lead.preferred_country}) - {int(hours_overdue)}h overdue\n"
    
    if len(leads) > 10:
        body += f"\n...and {len(leads) - 10} more.\n"
    
    body += "\nPlease prioritize these follow-ups today. 🎯"
    
    return body


def format_reminder_email(counselor_name: str, leads: List) -> str:
    """Format follow-up reminder email"""
    body = f"""
Hi {counselor_name},

Reminder: You have {len(leads)} follow-ups scheduled in the next 2 hours:

"""
    for lead in leads:
        time_str = lead.next_follow_up.strftime('%I:%M %p')
        body += f"- {lead.name} at {time_str} - {lead.course_interested}\n"
    
    body += "\nGood luck with your calls! 📞"
    
    return body


print("✅ Scheduled jobs loaded")
