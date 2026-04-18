"""
Background Tasks for Async Processing
Handles bulk operations, AI tasks, and heavy computations
"""

from celery_config import celery_app
from database import SessionLocal, Lead as DBLead, User as DBUser, Activity as DBActivity
from sqlalchemy.orm import Session
from datetime import datetime
import joblib
import pandas as pd
from typing import List, Dict, Any
import requests
import json
from logger_config import logger

# ============================================================================
# BULK OPERATIONS
# ============================================================================

@celery_app.task(bind=True, name='background_tasks.bulk_update_leads')
def bulk_update_leads(self, lead_ids: List[str], updates: Dict[str, Any], user_id: int):
    """
    Update multiple leads in background
    
    Args:
        lead_ids: List of lead IDs to update
        updates: Dictionary of fields to update
        user_id: User performing the update
    """
    db = SessionLocal()
    try:
        updated_count = 0
        failed_count = 0
        
        total = len(lead_ids)
        
        for idx, lead_id in enumerate(lead_ids):
            try:
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={'current': idx + 1, 'total': total, 'status': f'Updating lead {idx + 1}/{total}'}
                )
                
                lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
                if lead:
                    # Apply updates
                    for field, value in updates.items():
                        if hasattr(lead, field):
                            setattr(lead, field, value)
                    
                    lead.updated_at = datetime.utcnow()
                    
                    # Log activity
                    activity = DBActivity(
                        lead_id=lead.id,
                        user_id=user_id,
                        activity_type='bulk_update',
                        description=f"Bulk updated: {', '.join(updates.keys())}",
                        metadata=updates
                    )
                    db.add(activity)
                    
                    updated_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to update lead {lead_id}: {e}")
                failed_count += 1
                continue
        
        db.commit()
        
        logger.info(f"Bulk update completed: {updated_count} updated, {failed_count} failed")
        
        return {
            'status': 'completed',
            'updated': updated_count,
            'failed': failed_count,
            'total': total
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk update task failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name='background_tasks.bulk_delete_leads')
def bulk_delete_leads(self, lead_ids: List[str], user_id: int):
    """Delete multiple leads in background"""
    db = SessionLocal()
    try:
        deleted_count = 0
        total = len(lead_ids)
        
        for idx, lead_id in enumerate(lead_ids):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'current': idx + 1, 'total': total}
                )
                
                lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
                if lead:
                    # Log before deletion
                    activity = DBActivity(
                        lead_id=lead.id,
                        user_id=user_id,
                        activity_type='delete',
                        description=f"Lead deleted: {lead.name}"
                    )
                    db.add(activity)
                    db.commit()
                    
                    # Delete
                    db.delete(lead)
                    deleted_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to delete lead {lead_id}: {e}")
                continue
        
        db.commit()
        
        return {
            'status': 'completed',
            'deleted': deleted_count,
            'total': total
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk delete task failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name='background_tasks.bulk_assign_leads')
def bulk_assign_leads(self, lead_ids: List[str], strategy: str, hospital_id: int, user_id: int):
    """Auto-assign multiple leads using specified strategy"""
    from auto_assignment_orchestrator import AutoAssignmentOrchestrator
    
    db = SessionLocal()
    try:
        orchestrator = AutoAssignmentOrchestrator(db)
        
        assigned_count = 0
        total = len(lead_ids)
        
        for idx, lead_id in enumerate(lead_ids):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'current': idx + 1, 'total': total}
                )
                
                # Get lead internal ID
                lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
                if lead:
                    result = orchestrator.assign_lead(
                        lead_id=lead.id,
                        strategy=strategy,
                        hospital_id=hospital_id
                    )
                    
                    if result['success']:
                        assigned_count += 1
                        
            except Exception as e:
                logger.error(f"Failed to assign lead {lead_id}: {e}")
                continue
        
        return {
            'status': 'completed',
            'assigned': assigned_count,
            'total': total
        }
        
    except Exception as e:
        logger.error(f"Bulk assign task failed: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# AI TASKS
# ============================================================================

@celery_app.task(bind=True, name='background_tasks.ai_score_lead')
def ai_score_lead(self, lead_id: str):
    """Score single lead using AI model"""
    db = SessionLocal()
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
        if not lead:
            return {'status': 'not_found'}
        
        # Load model
        model_path = 'models/lead_conversion_model_latest.cbm'
        model = joblib.load(model_path)
        
        # Prepare features
        features = prepare_lead_features(lead)
        
        # Predict
        score = model.predict_proba([features])[0][1] * 100
        
        # Update lead
        lead.ai_score = round(score, 2)
        
        # Update segment
        if score >= 70:
            lead.ai_segment = 'Hot'
        elif score >= 40:
            lead.ai_segment = 'Warm'
        else:
            lead.ai_segment = 'Cold'
        
        lead.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Lead {lead_id} scored: {score:.2f}")
        
        return {
            'status': 'completed',
            'lead_id': lead_id,
            'score': score
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"AI scoring failed for {lead_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name='background_tasks.ai_score_bulk_leads')
def ai_score_bulk_leads(self, lead_ids: List[str]):
    """Score multiple leads using AI model (batch processing)"""
    db = SessionLocal()
    try:
        # Load model once
        model_path = 'models/lead_conversion_model_latest.cbm'
        model = joblib.load(model_path)
        
        scored_count = 0
        total = len(lead_ids)
        
        for idx, lead_id in enumerate(lead_ids):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'current': idx + 1, 'total': total}
                )
                
                lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
                if lead:
                    features = prepare_lead_features(lead)
                    score = model.predict_proba([features])[0][1] * 100
                    
                    lead.ai_score = round(score, 2)
                    
                    if score >= 70:
                        lead.ai_segment = 'Hot'
                    elif score >= 40:
                        lead.ai_segment = 'Warm'
                    else:
                        lead.ai_segment = 'Cold'
                    
                    lead.updated_at = datetime.utcnow()
                    scored_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to score lead {lead_id}: {e}")
                continue
        
        db.commit()
        
        return {
            'status': 'completed',
            'scored': scored_count,
            'total': total
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk AI scoring failed: {e}")
        raise
    finally:
        db.close()


def prepare_lead_features(lead) -> List[float]:
    """Prepare feature vector for ML model"""
    # This should match your model's expected features
    # Simplified version - adjust based on your actual model
    return [
        lead.ai_score or 0,
        1 if lead.status == 'hot' else 0,
        len(lead.notes or '') / 100,
        1 if lead.phone else 0,
        1 if lead.email else 0,
        # Add more features as needed
    ]


# ============================================================================
# DATA EXPORT TASKS
# ============================================================================

@celery_app.task(bind=True, name='background_tasks.export_leads_to_csv')
def export_leads_to_csv(self, filters: Dict[str, Any], user_id: int):
    """Export filtered leads to CSV"""
    db = SessionLocal()
    try:
        # Build query
        query = db.query(DBLead)
        
        # Apply filters
        if 'status' in filters:
            query = query.filter(DBLead.status == filters['status'])
        if 'country' in filters:
            query = query.filter(DBLead.preferred_country == filters['country'])
        if 'min_score' in filters:
            query = query.filter(DBLead.ai_score >= filters['min_score'])
        
        leads = query.all()
        
        # Convert to DataFrame
        data = []
        for lead in leads:
            data.append({
                'Lead ID': lead.lead_id,
                'Name': lead.name,
                'Email': lead.email,
                'Phone': lead.phone,
                'Country': lead.preferred_country,
                'Course': lead.course_interested,
                'Status': lead.status,
                'AI Score': lead.ai_score,
                'Segment': lead.ai_segment,
                'Created': lead.created_at,
                'Updated': lead.updated_at
            })
        
        df = pd.DataFrame(data)
        
        # Save to file
        filename = f"exports/leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        
        logger.info(f"Exported {len(leads)} leads to {filename}")
        
        return {
            'status': 'completed',
            'filename': filename,
            'count': len(leads)
        }
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# CLEANUP TASKS
# ============================================================================

@celery_app.task(name='background_tasks.cleanup_old_drafts')
def cleanup_old_drafts():
    """Clean up old draft data from localStorage (server-side cleanup)"""
    # This would clean server-side cached drafts if we stored them
    # For now, this is a placeholder
    logger.info("Draft cleanup completed")
    return {'status': 'completed'}


@celery_app.task(name='background_tasks.archive_old_leads')
def archive_old_leads(days: int = 365):
    """Archive leads older than specified days with no activity"""
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find inactive leads
        old_leads = db.query(DBLead).filter(
            DBLead.updated_at < cutoff_date,
            DBLead.status.in_(['cold', 'lost', 'not_interested'])
        ).all()
        
        archived_count = 0
        for lead in old_leads:
            # Mark as archived (you might want to move to separate table)
            lead.status = 'archived'
            lead.updated_at = datetime.utcnow()
            archived_count += 1
        
        db.commit()
        
        logger.info(f"Archived {archived_count} old leads")
        
        return {
            'status': 'completed',
            'archived': archived_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Archive task failed: {e}")
        raise
    finally:
        db.close()


print("✅ Background tasks loaded")
