"""
Celery Configuration for Background Tasks
Handles async processing, scheduled jobs, and task queues
"""

from celery import Celery
from celery.schedules import crontab
import os
from datetime import timedelta

# Redis connection string
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery
celery_app = Celery(
    'crm_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'background_tasks',
        'scheduled_jobs',
        'message_queue'
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # Soft limit at 25 minutes
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Task routing
    task_routes={
        'background_tasks.bulk_*': {'queue': 'bulk'},
        'background_tasks.ai_*': {'queue': 'ai'},
        'scheduled_jobs.*': {'queue': 'scheduled'},
        'message_queue.send_*': {'queue': 'messages'},
    },
    
    # Task priority
    task_default_priority=5,
    task_inherit_parent_priority=True,
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # Max 10 minutes
    task_retry_jitter=True,
)

# Scheduled Tasks (Beat Schedule)
celery_app.conf.beat_schedule = {
    # Daily lead scoring update (every day at 2 AM)
    'daily-lead-scoring': {
        'task': 'scheduled_jobs.update_all_lead_scores',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Auto-assign unassigned leads (every 2 hours during work hours)
    'auto-assign-leads': {
        'task': 'scheduled_jobs.auto_assign_unassigned_leads',
        'schedule': crontab(hour='9-17/2', minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Check overdue follow-ups (every hour)
    'check-overdue-followups': {
        'task': 'scheduled_jobs.send_overdue_followup_alerts',
        'schedule': crontab(minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Daily counselor performance report (every day at 8 AM)
    'daily-performance-report': {
        'task': 'scheduled_jobs.send_daily_performance_report',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Weekly summary report (Monday at 9 AM)
    'weekly-summary-report': {
        'task': 'scheduled_jobs.send_weekly_summary_report',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Sync Google Sheets (every 30 minutes)
    'sync-google-sheets': {
        'task': 'scheduled_jobs.sync_google_sheets_data',
        'schedule': timedelta(minutes=30),
        'options': {'queue': 'scheduled'}
    },
    
    # Clean up old activities (every day at 3 AM)
    'cleanup-old-activities': {
        'task': 'scheduled_jobs.cleanup_old_activities',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Re-engage stale leads (every day at 10 AM)
    'reengage-stale-leads': {
        'task': 'scheduled_jobs.trigger_stale_lead_workflow',
        'schedule': crontab(hour=10, minute=0),
        'options': {'queue': 'scheduled'}
    },
    
    # Send follow-up reminders (every 2 hours during work hours)
    'followup-reminders': {
        'task': 'scheduled_jobs.send_followup_reminders',
        'schedule': crontab(hour='8-18/2', minute=30),
        'options': {'queue': 'scheduled'}
    },
    
    # Cache warm-up (every day at 1 AM)
    'warm-cache': {
        'task': 'scheduled_jobs.warm_application_cache',
        'schedule': crontab(hour=1, minute=0),
        'options': {'queue': 'scheduled'}
    },
}

# Task annotations
celery_app.conf.task_annotations = {
    'background_tasks.bulk_delete_leads': {'rate_limit': '10/m'},
    'message_queue.send_bulk_email': {'rate_limit': '100/m'},
    'message_queue.send_bulk_whatsapp': {'rate_limit': '50/m'},
}

# Event monitoring
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True

print("✅ Celery configured successfully")
print(f"📡 Broker: {REDIS_URL}")
print(f"📊 Beat schedule: {len(celery_app.conf.beat_schedule)} scheduled tasks")
