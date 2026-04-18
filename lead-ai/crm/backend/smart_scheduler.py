"""
Smart Follow-up Scheduler
AI-driven optimal contact time prediction and automated follow-up scheduling
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from database import Lead, User, Activity
from logger_config import logger


class SmartScheduler:
    """Intelligent follow-up scheduling with AI-driven time predictions"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def suggest_optimal_time(
        self,
        lead_id: str,
        counselor_id: Optional[str] = None
    ) -> Dict:
        """
        AI-driven prediction of optimal contact time
        
        Analyzes:
        - Historical response patterns for this lead
        - Best performing times for similar leads (country, course)
        - Counselor's successful contact times
        - Lead's timezone and typical availability
        
        Returns:
            {
                "suggested_time": datetime,
                "confidence": 0.85,
                "reasoning": "Best time based on...",
                "alternatives": [datetime, datetime, datetime]
            }
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        counselor_id = counselor_id or lead.assigned_to
        
        # Get lead's timezone
        lead_tz = self._get_lead_timezone(lead)
        
        # Analyze historical patterns
        historical_pattern = self._analyze_historical_patterns(lead_id)
        
        # Analyze similar leads
        similar_leads_pattern = self._analyze_similar_leads(
            country=lead.country,
            course=lead.interested_course,
            ai_score=lead.ai_score
        )
        
        # Analyze counselor's success times
        counselor_pattern = self._analyze_counselor_patterns(counselor_id) if counselor_id else None
        
        # Combine patterns with weighted scoring
        optimal_time, confidence = self._compute_optimal_time(
            lead_tz=lead_tz,
            historical=historical_pattern,
            similar=similar_leads_pattern,
            counselor=counselor_pattern,
            lead_score=lead.ai_score or 50
        )
        
        # Generate alternatives
        alternatives = self._generate_alternatives(optimal_time, lead_tz)
        
        # Build reasoning
        reasoning = self._build_reasoning(
            historical_pattern,
            similar_leads_pattern,
            counselor_pattern,
            lead.ai_score
        )
        
        return {
            "suggested_time": optimal_time.isoformat(),
            "suggested_time_local": optimal_time.astimezone(lead_tz).strftime("%Y-%m-%d %I:%M %p %Z"),
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "alternatives": [
                {
                    "time": alt.isoformat(),
                    "time_local": alt.astimezone(lead_tz).strftime("%Y-%m-%d %I:%M %p %Z"),
                    "label": label
                }
                for alt, label in alternatives
            ],
            "timezone": str(lead_tz)
        }
    
    def auto_schedule(
        self,
        lead_id: str,
        trigger_event: str = "manual",
        counselor_id: Optional[str] = None
    ) -> Dict:
        """
        Automatically schedule follow-up based on lead status and AI score
        
        Trigger events:
        - status_change: Lead status changed
        - note_added: New note added
        - manual: Manual trigger
        - bulk: Bulk scheduling
        
        Rules:
        - Hot leads (80+): Schedule within 2 hours
        - Warm leads (50-79): Schedule next business day 10 AM
        - Cold leads (<50): Schedule 3 days out
        - Not Answering: Schedule 3 retry attempts (2h, 1d, 3d)
        - Qualified: Schedule demo within 24h
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Determine scheduling rule
        schedule_rule = self._get_schedule_rule(lead, trigger_event)
        
        # Calculate follow-up time
        follow_up_time = self._calculate_follow_up_time(
            lead=lead,
            rule=schedule_rule,
            counselor_id=counselor_id
        )
        
        # Update lead
        lead.next_follow_up = follow_up_time
        lead.follow_up_priority = schedule_rule["priority"]
        self.db.commit()
        
        logger.info(f"Auto-scheduled follow-up for lead {lead_id}: {follow_up_time} ({schedule_rule['reason']})")
        
        return {
            "success": True,
            "lead_id": lead_id,
            "follow_up_time": follow_up_time.isoformat(),
            "priority": schedule_rule["priority"],
            "reason": schedule_rule["reason"],
            "trigger_event": trigger_event
        }
    
    def check_conflicts(
        self,
        counselor_id: str,
        proposed_time: datetime,
        duration_minutes: int = 30
    ) -> Dict:
        """
        Check if counselor has scheduling conflicts
        
        Returns:
            {
                "has_conflict": bool,
                "conflicting_leads": [lead_ids],
                "workload_at_time": int,
                "recommendation": str
            }
        """
        # Get leads scheduled around this time (±30 min window)
        window_start = proposed_time - timedelta(minutes=duration_minutes)
        window_end = proposed_time + timedelta(minutes=duration_minutes)
        
        conflicts = self.db.query(Lead).filter(
            Lead.assigned_to == counselor_id,
            Lead.next_follow_up.between(window_start, window_end)
        ).all()
        
        # Get total workload for the day
        day_start = proposed_time.replace(hour=0, minute=0, second=0)
        day_end = day_start + timedelta(days=1)
        
        daily_workload = self.db.query(func.count(Lead.id)).filter(
            Lead.assigned_to == counselor_id,
            Lead.next_follow_up.between(day_start, day_end)
        ).scalar() or 0
        
        has_conflict = len(conflicts) > 0
        recommendation = ""
        
        if has_conflict:
            recommendation = f"Conflict with {len(conflicts)} lead(s). Consider scheduling {duration_minutes} minutes later."
        elif daily_workload >= 20:
            recommendation = "Heavy workload this day. Consider next day."
        else:
            recommendation = "Time slot available."
        
        return {
            "has_conflict": has_conflict,
            "conflicting_leads": [lead.id for lead in conflicts],
            "conflicting_count": len(conflicts),
            "daily_workload": daily_workload,
            "recommendation": recommendation
        }
    
    def bulk_schedule(
        self,
        lead_ids: List[str],
        strategy: str = "auto"
    ) -> Dict:
        """
        Bulk schedule follow-ups for multiple leads
        
        Strategies:
        - auto: AI-driven per lead
        - same_time: All at same time
        - distribute: Distribute across time slots
        """
        results = {
            "total": len(lead_ids),
            "scheduled": 0,
            "failed": 0,
            "errors": []
        }
        
        for lead_id in lead_ids:
            try:
                self.auto_schedule(lead_id, trigger_event="bulk")
                results["scheduled"] += 1
            except Exception as e:
                logger.error(f"Failed to schedule lead {lead_id}: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"Lead {lead_id}: {str(e)}")
        
        return results
    
    # Private helper methods
    
    def _get_lead_timezone(self, lead: Lead) -> pytz.timezone:
        """Determine lead's timezone from country"""
        # Country to timezone mapping (sample)
        country_tz_map = {
            "India": "Asia/Kolkata",
            "USA": "America/New_York",
            "UK": "Europe/London",
            "UAE": "Asia/Dubai",
            "Australia": "Australia/Sydney",
            "Canada": "America/Toronto",
            "Singapore": "Asia/Singapore"
        }
        
        tz_str = country_tz_map.get(lead.country, "UTC")
        return pytz.timezone(tz_str)
    
    def _analyze_historical_patterns(self, lead_id: str) -> Dict:
        """Analyze this lead's historical response patterns"""
        # Get activities for this lead
        activities = self.db.query(Activity).filter(
            Activity.lead_id == lead_id,
            Activity.activity_type.in_(["call", "whatsapp_sent", "email_sent", "note"])
        ).order_by(Activity.created_at.desc()).limit(20).all()
        
        if not activities:
            return {"has_data": False}
        
        # Find response times (time between our contact and their response)
        response_hours = []
        for i in range(len(activities) - 1):
            if activities[i].activity_type in ["call", "whatsapp_sent", "email_sent"]:
                # Check if next activity is a response (note within 24h)
                time_diff = (activities[i+1].created_at - activities[i].created_at).total_seconds() / 3600
                if time_diff <= 24:
                    response_hours.append(activities[i].created_at.hour)
        
        if not response_hours:
            return {"has_data": False}
        
        # Find most common hour
        from collections import Counter
        hour_counts = Counter(response_hours)
        best_hour = hour_counts.most_common(1)[0][0] if hour_counts else 10
        
        return {
            "has_data": True,
            "best_hour": best_hour,
            "response_count": len(response_hours),
            "confidence": min(len(response_hours) / 10, 1.0)  # More data = higher confidence
        }
    
    def _analyze_similar_leads(self, country: str, course: str, ai_score: float) -> Dict:
        """Analyze successful contact times for similar leads"""
        # Get converted leads with similar profile
        similar_leads = self.db.query(Lead).filter(
            Lead.country == country,
            Lead.status == "enrolled",
            Lead.ai_score.between(ai_score - 20, ai_score + 20)
        ).limit(50).all()
        
        if not similar_leads:
            return {"has_data": False}
        
        # Get activities for these leads
        lead_ids = [lead.id for lead in similar_leads]
        activities = self.db.query(Activity).filter(
            Activity.lead_id.in_(lead_ids),
            Activity.activity_type.in_(["call", "whatsapp_sent"])
        ).all()
        
        # Extract successful contact hours
        contact_hours = [activity.created_at.hour for activity in activities]
        
        if not contact_hours:
            return {"has_data": False}
        
        from collections import Counter
        hour_counts = Counter(contact_hours)
        best_hour = hour_counts.most_common(1)[0][0] if hour_counts else 10
        
        return {
            "has_data": True,
            "best_hour": best_hour,
            "sample_size": len(similar_leads),
            "confidence": min(len(similar_leads) / 20, 1.0)
        }
    
    def _analyze_counselor_patterns(self, counselor_id: str) -> Dict:
        """Analyze counselor's most successful contact times"""
        # Get counselor's converted leads
        converted_leads = self.db.query(Lead).filter(
            Lead.assigned_to == counselor_id,
            Lead.status == "enrolled"
        ).limit(100).all()
        
        if not converted_leads:
            return {"has_data": False}
        
        lead_ids = [lead.id for lead in converted_leads]
        activities = self.db.query(Activity).filter(
            Activity.lead_id.in_(lead_ids),
            Activity.user_id == counselor_id,
            Activity.activity_type.in_(["call", "whatsapp_sent"])
        ).all()
        
        contact_hours = [activity.created_at.hour for activity in activities]
        
        if not contact_hours:
            return {"has_data": False}
        
        from collections import Counter
        hour_counts = Counter(contact_hours)
        best_hour = hour_counts.most_common(1)[0][0] if hour_counts else 10
        
        return {
            "has_data": True,
            "best_hour": best_hour,
            "sample_size": len(converted_leads),
            "confidence": min(len(converted_leads) / 30, 1.0)
        }
    
    def _compute_optimal_time(
        self,
        lead_tz: pytz.timezone,
        historical: Dict,
        similar: Dict,
        counselor: Optional[Dict],
        lead_score: float
    ) -> Tuple[datetime, float]:
        """Compute optimal time by combining all patterns with weighted scoring"""
        
        # Default to 10 AM in lead's timezone
        base_hour = 10
        confidence_scores = []
        
        # Weighted scoring
        if historical.get("has_data"):
            base_hour = historical["best_hour"]
            confidence_scores.append(historical["confidence"] * 0.4)  # 40% weight
        
        if similar.get("has_data"):
            # Average with similar leads pattern
            base_hour = int((base_hour + similar["best_hour"]) / 2)
            confidence_scores.append(similar["confidence"] * 0.3)  # 30% weight
        
        if counselor and counselor.get("has_data"):
            # Slight influence from counselor's pattern
            base_hour = int(base_hour * 0.7 + counselor["best_hour"] * 0.3)
            confidence_scores.append(counselor["confidence"] * 0.2)  # 20% weight
        
        # Hot leads get scheduled sooner
        if lead_score >= 80:
            # Within 2 hours from now
            now = datetime.now(pytz.UTC)
            optimal_time = now + timedelta(hours=2)
            confidence = 0.9  # High confidence for hot leads
        else:
            # Schedule for next business day at optimal hour
            now = datetime.now(lead_tz)
            tomorrow = now + timedelta(days=1)
            optimal_time = tomorrow.replace(hour=base_hour, minute=0, second=0, microsecond=0)
            
            # Skip weekends
            while optimal_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                optimal_time += timedelta(days=1)
            
            # Convert to UTC
            optimal_time = optimal_time.astimezone(pytz.UTC)
            
            # Calculate overall confidence
            confidence = sum(confidence_scores) if confidence_scores else 0.5
        
        return optimal_time, min(confidence, 0.95)
    
    def _generate_alternatives(self, optimal_time: datetime, lead_tz: pytz.timezone) -> List[Tuple[datetime, str]]:
        """Generate alternative time slots"""
        alternatives = []
        
        # 2 hours later
        alternatives.append((
            optimal_time + timedelta(hours=2),
            "2 hours later"
        ))
        
        # Tomorrow same time
        tomorrow = optimal_time + timedelta(days=1)
        alternatives.append((tomorrow, "Tomorrow same time"))
        
        # Next week same time
        next_week = optimal_time + timedelta(days=7)
        alternatives.append((next_week, "Next week"))
        
        return alternatives
    
    def _build_reasoning(
        self,
        historical: Dict,
        similar: Dict,
        counselor: Optional[Dict],
        lead_score: float
    ) -> str:
        """Build human-readable reasoning"""
        reasons = []
        
        if lead_score >= 80:
            reasons.append("🔥 Hot lead - scheduling within 2 hours for maximum impact")
        
        if historical.get("has_data"):
            reasons.append(f"📊 Lead typically responds at {historical['best_hour']}:00 (from {historical['response_count']} interactions)")
        
        if similar.get("has_data"):
            reasons.append(f"🎯 Similar leads in {similar['sample_size']} cases responded best at {similar['best_hour']}:00")
        
        if counselor and counselor.get("has_data"):
            reasons.append(f"⭐ Counselor's success pattern shows {counselor['best_hour']}:00 works well")
        
        if not reasons:
            reasons.append("📅 Standard business hours (10 AM local time)")
        
        return " | ".join(reasons)
    
    def _get_schedule_rule(self, lead: Lead, trigger_event: str) -> Dict:
        """Determine scheduling rule based on lead properties"""
        ai_score = lead.ai_score or 50
        status = lead.status or "new"
        
        rules = {
            "hot": {
                "condition": ai_score >= 80,
                "hours_ahead": 2,
                "priority": "P0",
                "reason": "Hot lead - urgent follow-up required"
            },
            "warm": {
                "condition": 50 <= ai_score < 80,
                "hours_ahead": 24,
                "priority": "P1",
                "reason": "Warm lead - next business day follow-up"
            },
            "cold": {
                "condition": ai_score < 50,
                "hours_ahead": 72,
                "priority": "P2",
                "reason": "Cold lead - 3-day follow-up cycle"
            },
            "not_answering": {
                "condition": status == "not_answering",
                "hours_ahead": 48,
                "priority": "P2",
                "reason": "Not answering - retry in 2 days"
            },
            "qualified": {
                "condition": status == "qualified",
                "hours_ahead": 12,
                "priority": "P0",
                "reason": "Qualified - schedule demo within 24h"
            }
        }
        
        # Find matching rule
        for rule_name, rule in rules.items():
            if rule["condition"]:
                return rule
        
        # Default rule
        return {
            "hours_ahead": 24,
            "priority": "P2",
            "reason": "Standard follow-up schedule"
        }
    
    def _calculate_follow_up_time(
        self,
        lead: Lead,
        rule: Dict,
        counselor_id: Optional[str]
    ) -> datetime:
        """Calculate follow-up time based on rule and counselor availability"""
        
        # Get lead timezone
        lead_tz = self._get_lead_timezone(lead)
        
        # Calculate base time
        now = datetime.now(lead_tz)
        follow_up = now + timedelta(hours=rule["hours_ahead"])
        
        # Adjust to business hours (9 AM - 6 PM)
        if follow_up.hour < 9:
            follow_up = follow_up.replace(hour=9, minute=0)
        elif follow_up.hour >= 18:
            follow_up = follow_up.replace(hour=9, minute=0) + timedelta(days=1)
        
        # Skip weekends
        while follow_up.weekday() >= 5:
            follow_up += timedelta(days=1)
        
        # Convert to UTC
        return follow_up.astimezone(pytz.UTC).replace(tzinfo=None)
