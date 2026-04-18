"""
Advanced Analytics Engine
Comprehensive analytics for lead attribution, conversion funnels, performance tracking
"""

from database import SessionLocal, Lead as DBLead, User as DBUser, Activity as DBActivity
from sqlalchemy import func, and_, or_, case, distinct
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from logger_config import logger
from collections import defaultdict
import pandas as pd
import numpy as np

class AnalyticsEngine:
    """
    Advanced analytics engine for CRM insights
    """
    
    def __init__(self, db=None):
        self.db = db or SessionLocal()
    
    # ============================================================================
    # LEAD SOURCE ATTRIBUTION
    # ============================================================================
    
    def get_lead_source_attribution(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        hospital_id: Optional[int] = None
    ) -> Dict:
        """
        Analyze lead sources and their conversion performance
        
        Returns:
            - Total leads per source
            - Conversion rate per source
            - Revenue per source (if available)
            - Cost per lead (CPL)
            - ROI per source
        """
        try:
            # Default to last 30 days
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            query = self.db.query(DBLead).filter(
                DBLead.created_at >= start_date,
                DBLead.created_at <= end_date
            )
            
            if hospital_id:
                query = query.filter(DBLead.hospital_id == hospital_id)
            
            leads = query.all()
            
            # Group by source
            source_stats = defaultdict(lambda: {
                'total_leads': 0,
                'contacted': 0,
                'qualified': 0,
                'enrolled': 0,
                'conversion_rate': 0,
                'avg_score': 0,
                'total_score': 0
            })
            
            for lead in leads:
                source = lead.source or 'Unknown'
                source_stats[source]['total_leads'] += 1
                source_stats[source]['total_score'] += lead.ai_score or 0
                
                if lead.status in ['contacted', 'qualified', 'enrolled']:
                    source_stats[source]['contacted'] += 1
                if lead.status in ['qualified', 'enrolled']:
                    source_stats[source]['qualified'] += 1
                if lead.status == 'enrolled':
                    source_stats[source]['enrolled'] += 1
            
            # Calculate metrics
            results = []
            for source, stats in source_stats.items():
                total = stats['total_leads']
                if total > 0:
                    stats['avg_score'] = round(stats['total_score'] / total, 1)
                    stats['conversion_rate'] = round((stats['enrolled'] / total) * 100, 2)
                    stats['contact_rate'] = round((stats['contacted'] / total) * 100, 2)
                    stats['qualification_rate'] = round((stats['qualified'] / total) * 100, 2)
                
                del stats['total_score']  # Remove temporary field
                
                results.append({
                    'source': source,
                    **stats
                })
            
            # Sort by total leads (descending)
            results.sort(key=lambda x: x['total_leads'], reverse=True)
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'sources': results,
                'total_leads': len(leads),
                'top_source': results[0]['source'] if results else None
            }
            
        except Exception as e:
            logger.error(f"Lead source attribution error: {e}")
            raise
    
    # ============================================================================
    # CONVERSION FUNNEL ANALYTICS
    # ============================================================================
    
    def get_conversion_funnel(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        hospital_id: Optional[int] = None,
        segment: Optional[str] = None
    ) -> Dict:
        """
        Calculate conversion funnel metrics
        
        Stages:
        1. New (created)
        2. Contacted (first contact made)
        3. Qualified (interested + viable)
        4. Enrolled (converted)
        """
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            query = self.db.query(DBLead).filter(
                DBLead.created_at >= start_date,
                DBLead.created_at <= end_date
            )
            
            if hospital_id:
                query = query.filter(DBLead.hospital_id == hospital_id)
            
            if segment:
                query = query.filter(DBLead.ai_segment == segment)
            
            leads = query.all()
            
            # Calculate funnel stages
            funnel = {
                'new': len(leads),
                'contacted': 0,
                'qualified': 0,
                'enrolled': 0
            }
            
            # Time spent in each stage
            stage_durations = {
                'new_to_contact': [],
                'contact_to_qualified': [],
                'qualified_to_enrolled': []
            }
            
            for lead in leads:
                # Contacted
                if lead.status in ['contacted', 'qualified', 'enrolled', 'warm', 'hot']:
                    funnel['contacted'] += 1
                    
                    if lead.last_contacted and lead.created_at:
                        duration = (lead.last_contacted - lead.created_at).total_seconds() / 3600
                        stage_durations['new_to_contact'].append(duration)
                
                # Qualified
                if lead.status in ['qualified', 'enrolled']:
                    funnel['qualified'] += 1
                
                # Enrolled
                if lead.status == 'enrolled':
                    funnel['enrolled'] += 1
            
            # Calculate conversion rates
            conversion_rates = {}
            if funnel['new'] > 0:
                conversion_rates['new_to_contacted'] = round((funnel['contacted'] / funnel['new']) * 100, 2)
            if funnel['contacted'] > 0:
                conversion_rates['contacted_to_qualified'] = round((funnel['qualified'] / funnel['contacted']) * 100, 2)
            if funnel['qualified'] > 0:
                conversion_rates['qualified_to_enrolled'] = round((funnel['enrolled'] / funnel['qualified']) * 100, 2)
            if funnel['new'] > 0:
                conversion_rates['overall'] = round((funnel['enrolled'] / funnel['new']) * 100, 2)
            
            # Average time in stages
            avg_durations = {}
            for stage, durations in stage_durations.items():
                if durations:
                    avg_durations[stage] = round(np.mean(durations), 1)
                else:
                    avg_durations[stage] = 0
            
            # Drop-off analysis
            dropoff = {
                'new_to_contacted': funnel['new'] - funnel['contacted'],
                'contacted_to_qualified': funnel['contacted'] - funnel['qualified'],
                'qualified_to_enrolled': funnel['qualified'] - funnel['enrolled']
            }
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'funnel_stages': funnel,
                'conversion_rates': conversion_rates,
                'avg_durations_hours': avg_durations,
                'dropoff': dropoff,
                'total_leads': funnel['new'],
                'final_conversion_rate': conversion_rates.get('overall', 0)
            }
            
        except Exception as e:
            logger.error(f"Conversion funnel error: {e}")
            raise
    
    # ============================================================================
    # COUNSELOR PERFORMANCE LEADERBOARD
    # ============================================================================
    
    def get_counselor_leaderboard(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        metric: str = 'enrollments',
        hospital_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Generate counselor performance leaderboard
        
        Metrics:
        - enrollments: Total enrollments
        - conversion_rate: Enrollment rate
        - activity: Total activities
        - response_time: Avg response time
        """
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get counselors
            counselor_query = self.db.query(DBUser).filter(
                DBUser.role.in_(['Counselor', 'Team Leader'])
            )
            
            if hospital_id:
                counselor_query = counselor_query.filter(DBUser.hospital_id == hospital_id)
            
            counselors = counselor_query.all()
            
            leaderboard = []
            
            for counselor in counselors:
                # Get leads assigned to counselor
                leads = self.db.query(DBLead).filter(
                    DBLead.assigned_to == counselor.id,
                    DBLead.created_at >= start_date,
                    DBLead.created_at <= end_date
                ).all()
                
                # Get activities
                activities = self.db.query(DBActivity).filter(
                    DBActivity.user_id == counselor.id,
                    DBActivity.created_at >= start_date,
                    DBActivity.created_at <= end_date
                ).all()
                
                # Calculate metrics
                total_leads = len(leads)
                enrollments = len([l for l in leads if l.status == 'enrolled'])
                calls_made = len([a for a in activities if a.activity_type in ['call', 'contacted']])
                emails_sent = len([a for a in activities if a.activity_type == 'email_sent'])
                whatsapp_sent = len([a for a in activities if a.activity_type == 'whatsapp_sent'])
                
                conversion_rate = 0
                if total_leads > 0:
                    conversion_rate = round((enrollments / total_leads) * 100, 2)
                
                # Calculate response time
                response_times = []
                for lead in leads:
                    if lead.last_contacted and lead.created_at:
                        response_time = (lead.last_contacted - lead.created_at).total_seconds() / 3600
                        response_times.append(response_time)
                
                avg_response_time = round(np.mean(response_times), 1) if response_times else 0
                
                # Score for ranking (weighted)
                score = (
                    enrollments * 10 +  # Enrollments weighted heavily
                    conversion_rate * 2 +
                    calls_made * 0.5 +
                    emails_sent * 0.3 +
                    whatsapp_sent * 0.3
                )
                
                leaderboard.append({
                    'counselor_id': counselor.id,
                    'name': counselor.name,
                    'email': counselor.email,
                    'role': counselor.role,
                    'total_leads': total_leads,
                    'enrollments': enrollments,
                    'conversion_rate': conversion_rate,
                    'calls_made': calls_made,
                    'emails_sent': emails_sent,
                    'whatsapp_sent': whatsapp_sent,
                    'total_activities': len(activities),
                    'avg_response_time_hours': avg_response_time,
                    'performance_score': round(score, 2)
                })
            
            # Sort by metric
            metric_map = {
                'enrollments': 'enrollments',
                'conversion_rate': 'conversion_rate',
                'activity': 'total_activities',
                'response_time': 'avg_response_time_hours'
            }
            
            sort_key = metric_map.get(metric, 'performance_score')
            reverse = True if sort_key != 'avg_response_time_hours' else False
            
            leaderboard.sort(key=lambda x: x[sort_key], reverse=reverse)
            
            # Add rank
            for idx, counselor in enumerate(leaderboard, 1):
                counselor['rank'] = idx
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Counselor leaderboard error: {e}")
            raise
    
    # ============================================================================
    # PREDICTIVE ANALYTICS
    # ============================================================================
    
    def predict_enrollment_probability(self, lead_id: str) -> Dict:
        """
        Predict probability of enrollment for a lead
        
        Uses multiple factors:
        - AI score
        - Current status
        - Days since creation
        - Activity count
        - Response rate
        """
        try:
            lead = self.db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
            
            if not lead:
                return {'error': 'Lead not found'}
            
            # Base probability from AI score
            base_prob = (lead.ai_score or 50) / 100
            
            # Status multiplier
            status_multipliers = {
                'new': 0.3,
                'contacted': 0.5,
                'qualified': 0.7,
                'warm': 0.6,
                'hot': 0.9,
                'cold': 0.2,
                'not_answering': 0.1,
                'enrolled': 1.0,
                'lost': 0.0
            }
            status_mult = status_multipliers.get(lead.status, 0.5)
            
            # Days since creation (decay over time)
            days_old = (datetime.utcnow() - lead.created_at).days
            time_decay = max(0.5, 1.0 - (days_old / 90))  # Decay over 90 days
            
            # Activity count (more activities = higher engagement)
            activities = self.db.query(DBActivity).filter(DBActivity.lead_id == lead.id).count()
            activity_boost = min(1.5, 1.0 + (activities / 20))  # Cap at 1.5x
            
            # Calculate final probability
            probability = base_prob * status_mult * time_decay * activity_boost
            probability = min(1.0, max(0.0, probability))  # Clamp to [0, 1]
            
            # Confidence based on data completeness
            confidence = 0.5
            if lead.ai_score:
                confidence += 0.2
            if activities > 5:
                confidence += 0.2
            if lead.last_contacted:
                confidence += 0.1
            
            confidence = min(1.0, confidence)
            
            return {
                'lead_id': lead_id,
                'enrollment_probability': round(probability * 100, 2),
                'confidence': round(confidence * 100, 2),
                'factors': {
                    'ai_score': lead.ai_score,
                    'status': lead.status,
                    'days_old': days_old,
                    'activity_count': activities,
                    'base_probability': round(base_prob * 100, 2),
                    'status_multiplier': status_mult,
                    'time_decay': round(time_decay, 2),
                    'activity_boost': round(activity_boost, 2)
                },
                'recommendation': self._get_enrollment_recommendation(probability)
            }
            
        except Exception as e:
            logger.error(f"Enrollment prediction error: {e}")
            raise
    
    def _get_enrollment_recommendation(self, probability: float) -> str:
        """Get action recommendation based on probability"""
        if probability >= 0.8:
            return "Very High - Close immediately, offer enrollment incentives"
        elif probability >= 0.6:
            return "High - Schedule enrollment call, send scholarship info"
        elif probability >= 0.4:
            return "Medium - Nurture with follow-ups, address concerns"
        elif probability >= 0.2:
            return "Low - Re-engage with personalized content"
        else:
            return "Very Low - Consider deprioritizing or re-qualification"
    
    def forecast_enrollments(
        self,
        forecast_days: int = 30,
        hospital_id: Optional[int] = None
    ) -> Dict:
        """
        Forecast enrollments for next N days based on historical trends
        """
        try:
            # Get historical data (last 90 days)
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            
            query = self.db.query(DBLead).filter(
                DBLead.created_at >= ninety_days_ago,
                DBLead.status == 'enrolled'
            )
            
            if hospital_id:
                query = query.filter(DBLead.hospital_id == hospital_id)
            
            enrolled_leads = query.all()
            
            # Group by week
            weekly_enrollments = defaultdict(int)
            for lead in enrolled_leads:
                week = lead.created_at.isocalendar()[1]
                weekly_enrollments[week] += 1
            
            # Calculate average weekly enrollment rate
            if weekly_enrollments:
                avg_weekly = np.mean(list(weekly_enrollments.values()))
            else:
                avg_weekly = 0
            
            # Forecast for next N days
            daily_rate = avg_weekly / 7
            forecasted_total = int(daily_rate * forecast_days)
            
            # Get current pipeline
            current_pipeline = self.db.query(DBLead).filter(
                DBLead.status.in_(['contacted', 'qualified', 'warm', 'hot']),
                DBLead.ai_score >= 50
            )
            
            if hospital_id:
                current_pipeline = current_pipeline.filter(DBLead.hospital_id == hospital_id)
            
            pipeline_count = current_pipeline.count()
            
            # Estimate based on pipeline + historical rate
            pipeline_conversion = pipeline_count * 0.15  # Assume 15% conversion
            forecast_with_pipeline = int(forecasted_total + pipeline_conversion)
            
            return {
                'forecast_period_days': forecast_days,
                'historical_avg_weekly': round(avg_weekly, 1),
                'forecasted_enrollments': forecasted_total,
                'current_pipeline': pipeline_count,
                'forecast_with_pipeline': forecast_with_pipeline,
                'confidence': 'Medium' if len(enrolled_leads) > 20 else 'Low',
                'daily_rate': round(daily_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Enrollment forecast error: {e}")
            raise
    
    # ============================================================================
    # ADVANCED SEGMENTATION
    # ============================================================================
    
    def create_segment(
        self,
        name: str,
        filters: Dict,
        user_id: int
    ) -> Dict:
        """
        Create a custom segment based on filters
        """
        try:
            query = self.db.query(DBLead)
            
            # Apply filters
            if 'status' in filters and filters['status']:
                query = query.filter(DBLead.status.in_(filters['status']))
            
            if 'ai_segment' in filters and filters['ai_segment']:
                query = query.filter(DBLead.ai_segment.in_(filters['ai_segment']))
            
            if 'score_min' in filters:
                query = query.filter(DBLead.ai_score >= filters['score_min'])
            
            if 'score_max' in filters:
                query = query.filter(DBLead.ai_score <= filters['score_max'])
            
            if 'countries' in filters and filters['countries']:
                query = query.filter(DBLead.preferred_country.in_(filters['countries']))
            
            if 'courses' in filters and filters['courses']:
                query = query.filter(DBLead.course_interested.in_(filters['courses']))
            
            if 'source' in filters and filters['source']:
                query = query.filter(DBLead.source.in_(filters['source']))
            
            if 'days_inactive_min' in filters:
                date_threshold = datetime.utcnow() - timedelta(days=filters['days_inactive_min'])
                query = query.filter(DBLead.updated_at <= date_threshold)
            
            leads = query.all()
            
            # Calculate segment stats
            total = len(leads)
            enrolled = len([l for l in leads if l.status == 'enrolled'])
            avg_score = np.mean([l.ai_score or 0 for l in leads]) if leads else 0
            
            return {
                'name': name,
                'filters': filters,
                'total_leads': total,
                'enrolled': enrolled,
                'conversion_rate': round((enrolled / total) * 100, 2) if total > 0 else 0,
                'avg_score': round(avg_score, 1),
                'created_by': user_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Segment creation error: {e}")
            raise
    
    # ============================================================================
    # DATA QUALITY MONITORING
    # ============================================================================
    
    def get_data_quality_report(self, hospital_id: Optional[int] = None) -> Dict:
        """
        Generate data quality report
        
        Checks:
        - Missing email/phone
        - Duplicate detection
        - Incomplete profiles
        - Invalid data patterns
        """
        try:
            query = self.db.query(DBLead)
            
            if hospital_id:
                query = query.filter(DBLead.hospital_id == hospital_id)
            
            leads = query.all()
            total = len(leads)
            
            # Missing data checks
            missing_email = len([l for l in leads if not l.email])
            missing_phone = len([l for l in leads if not l.phone])
            missing_course = len([l for l in leads if not l.course_interested])
            missing_country = len([l for l in leads if not l.preferred_country])
            
            # Duplicate detection (by email)
            emails = [l.email for l in leads if l.email]
            duplicates = len(emails) - len(set(emails))
            
            # Incomplete profiles (missing 2+ key fields)
            incomplete = 0
            for lead in leads:
                missing_count = 0
                if not lead.email: missing_count += 1
                if not lead.phone: missing_count += 1
                if not lead.course_interested: missing_count += 1
                if not lead.preferred_country: missing_count += 1
                
                if missing_count >= 2:
                    incomplete += 1
            
            # Stale leads (no activity in 30+ days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            stale = len([l for l in leads if l.updated_at < thirty_days_ago and l.status not in ['enrolled', 'lost']])
            
            # Calculate quality score
            quality_score = 100
            quality_score -= (missing_email / total) * 20 if total > 0 else 0
            quality_score -= (missing_phone / total) * 15 if total > 0 else 0
            quality_score -= (duplicates / total) * 25 if total > 0 else 0
            quality_score -= (incomplete / total) * 20 if total > 0 else 0
            quality_score -= (stale / total) * 20 if total > 0 else 0
            quality_score = max(0, quality_score)
            
            return {
                'total_leads': total,
                'quality_score': round(quality_score, 1),
                'issues': {
                    'missing_email': missing_email,
                    'missing_phone': missing_phone,
                    'missing_course': missing_course,
                    'missing_country': missing_country,
                    'duplicates': duplicates,
                    'incomplete_profiles': incomplete,
                    'stale_leads': stale
                },
                'recommendations': self._get_quality_recommendations(quality_score)
            }
            
        except Exception as e:
            logger.error(f"Data quality report error: {e}")
            raise
    
    def _get_quality_recommendations(self, score: float) -> List[str]:
        """Get recommendations based on quality score"""
        recommendations = []
        
        if score < 50:
            recommendations.append("🚨 Critical: Data quality is very poor. Immediate cleanup required.")
        elif score < 70:
            recommendations.append("⚠️ Warning: Data quality needs improvement.")
        
        if score < 80:
            recommendations.extend([
                "Run duplicate detection and merge",
                "Enable mandatory fields for email/phone",
                "Set up data validation rules",
                "Archive or delete stale leads"
            ])
        else:
            recommendations.append("✅ Data quality is good. Continue monitoring.")
        
        return recommendations


print("✅ Analytics engine loaded")
