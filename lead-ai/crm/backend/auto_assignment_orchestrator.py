"""
Intelligent Auto-Assignment Orchestrator
Handles automated lead assignment with multiple strategies:
- Intelligent (AI-driven based on performance, specialization, workload)
- Round-robin (equal distribution)
- Skill-based (country/course specialization matching)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from database import Lead, User
from logger_config import logger


class AutoAssignmentOrchestrator:
    """Orchestrates intelligent lead assignment across multiple strategies"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def assign_lead(
        self, 
        lead_id: str, 
        strategy: str = "intelligent",
        hospital_id: Optional[str] = None,
        preferred_country: Optional[str] = None,
        preferred_course: Optional[str] = None
    ) -> Dict:
        """
        Assign a single lead using specified strategy
        
        Args:
            lead_id: Lead ID to assign
            strategy: One of 'intelligent', 'round-robin', 'skill-based'
            hospital_id: Hospital scope (required for non-super-admins)
            preferred_country: Country preference for skill-based matching
            preferred_course: Course preference for skill-based matching
            
        Returns:
            Assignment result with counselor_id, score, and reasoning
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        if lead.assigned_to:
            logger.warning(f"Lead {lead_id} already assigned to {lead.assigned_to}")
            return {
                "success": False,
                "reason": "Lead already assigned",
                "current_assignee": lead.assigned_to
            }
        
        # Get eligible counselors
        eligible_counselors = self._get_eligible_counselors(
            hospital_id=hospital_id or lead.hospital_id,
            country=preferred_country or lead.country,
            course=preferred_course or lead.interested_course
        )
        
        if not eligible_counselors:
            raise ValueError("No eligible counselors found for assignment")
        
        # Select counselor based on strategy
        if strategy == "intelligent":
            counselor = self._intelligent_assignment(lead, eligible_counselors)
        elif strategy == "round-robin":
            counselor = self._round_robin_assignment(eligible_counselors)
        elif strategy == "skill-based":
            counselor = self._skill_based_assignment(lead, eligible_counselors)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Assign the lead
        lead.assigned_to = counselor["user_id"]
        lead.assigned_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Lead {lead_id} assigned to {counselor['user_id']} using {strategy} strategy")
        
        return {
            "success": True,
            "lead_id": lead_id,
            "counselor_id": counselor["user_id"],
            "counselor_name": counselor["name"],
            "strategy": strategy,
            "score": counselor.get("score", 0),
            "reasoning": counselor.get("reasoning", f"Assigned via {strategy} strategy")
        }
    
    def bulk_assign(
        self,
        lead_ids: List[str],
        strategy: str = "intelligent",
        hospital_id: Optional[str] = None
    ) -> Dict:
        """
        Bulk assign multiple leads with load balancing
        
        Args:
            lead_ids: List of lead IDs to assign
            strategy: Assignment strategy
            hospital_id: Hospital scope
            
        Returns:
            Summary of assignments (success count, failures, distribution)
        """
        results = {
            "total": len(lead_ids),
            "assigned": 0,
            "failed": 0,
            "skipped": 0,
            "distribution": {},
            "errors": []
        }
        
        # Get all leads at once
        leads = self.db.query(Lead).filter(
            Lead.id.in_(lead_ids),
            Lead.assigned_to.is_(None)
        ).all()
        
        if not leads:
            results["skipped"] = len(lead_ids)
            results["errors"].append("All leads already assigned or not found")
            return results
        
        # Get eligible counselors
        eligible_counselors = self._get_eligible_counselors(hospital_id=hospital_id)
        if not eligible_counselors:
            results["failed"] = len(leads)
            results["errors"].append("No eligible counselors found")
            return results
        
        # Assign leads with load balancing
        counselor_loads = {c["user_id"]: 0 for c in eligible_counselors}
        
        for lead in leads:
            try:
                # Get current workloads
                current_loads = self._get_current_workloads([c["user_id"] for c in eligible_counselors])
                
                # Select counselor based on strategy
                if strategy == "intelligent":
                    counselor = self._intelligent_assignment(lead, eligible_counselors, current_loads)
                elif strategy == "round-robin":
                    # Round-robin with load balancing
                    counselor = min(eligible_counselors, key=lambda c: current_loads.get(c["user_id"], 0) + counselor_loads.get(c["user_id"], 0))
                else:
                    counselor = self._skill_based_assignment(lead, eligible_counselors, current_loads)
                
                # Assign
                lead.assigned_to = counselor["user_id"]
                lead.assigned_at = datetime.utcnow()
                counselor_loads[counselor["user_id"]] += 1
                
                # Track distribution
                results["distribution"][counselor["name"]] = results["distribution"].get(counselor["name"], 0) + 1
                results["assigned"] += 1
                
            except Exception as e:
                logger.error(f"Failed to assign lead {lead.id}: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"Lead {lead.id}: {str(e)}")
        
        self.db.commit()
        logger.info(f"Bulk assignment complete: {results['assigned']}/{len(lead_ids)} assigned")
        
        return results
    
    def preview_assignment(
        self,
        lead_ids: List[str],
        strategy: str = "intelligent",
        hospital_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Preview assignment distribution without committing
        
        Returns:
            List of {lead_id, counselor_id, counselor_name, score, reasoning}
        """
        leads = self.db.query(Lead).filter(
            Lead.id.in_(lead_ids),
            Lead.assigned_to.is_(None)
        ).all()
        
        eligible_counselors = self._get_eligible_counselors(hospital_id=hospital_id)
        if not eligible_counselors:
            return []
        
        preview = []
        counselor_loads = {c["user_id"]: 0 for c in eligible_counselors}
        
        for lead in leads:
            current_loads = self._get_current_workloads([c["user_id"] for c in eligible_counselors])
            
            if strategy == "intelligent":
                counselor = self._intelligent_assignment(lead, eligible_counselors, current_loads)
            elif strategy == "round-robin":
                counselor = min(eligible_counselors, key=lambda c: current_loads.get(c["user_id"], 0) + counselor_loads.get(c["user_id"], 0))
            else:
                counselor = self._skill_based_assignment(lead, eligible_counselors, current_loads)
            
            counselor_loads[counselor["user_id"]] += 1
            
            preview.append({
                "lead_id": lead.id,
                "lead_name": lead.name,
                "lead_country": lead.country,
                "counselor_id": counselor["user_id"],
                "counselor_name": counselor["name"],
                "score": counselor.get("score", 0),
                "reasoning": counselor.get("reasoning", "")
            })
        
        return preview
    
    def _get_eligible_counselors(
        self,
        hospital_id: Optional[str] = None,
        country: Optional[str] = None,
        course: Optional[str] = None
    ) -> List[Dict]:
        """
        Get list of eligible counselors based on filters
        
        Returns:
            List of {user_id, name, email, role, specialization, performance}
        """
        query = self.db.query(User).filter(
            User.role.in_(["counselor", "team_leader", "manager"]),
            User.is_active == True
        )
        
        if hospital_id:
            query = query.filter(User.hospital_id == hospital_id)
        
        counselors = query.all()
        
        result = []
        for counselor in counselors:
            # Check working hours (timezone-aware)
            if not self._is_working_hours(counselor):
                continue
            
            counselor_data = {
                "user_id": counselor.id,
                "name": counselor.name,
                "email": counselor.email,
                "role": counselor.role,
                "hospital_id": counselor.hospital_id,
                "specialization": {
                    "countries": getattr(counselor, "specialized_countries", []),
                    "courses": getattr(counselor, "specialized_courses", [])
                },
                "performance": self._get_performance_score(counselor.id)
            }
            result.append(counselor_data)
        
        return result
    
    def _intelligent_assignment(
        self,
        lead: Lead,
        counselors: List[Dict],
        current_loads: Optional[Dict[str, int]] = None
    ) -> Dict:
        """
        AI-driven assignment based on:
        - Workload balance (30%)
        - Country/course specialization (30%)
        - Historical performance (25%)
        - Lead score (15%)
        """
        if current_loads is None:
            current_loads = self._get_current_workloads([c["user_id"] for c in counselors])
        
        scored_counselors = []
        
        for counselor in counselors:
            score = 0
            reasoning = []
            
            # Workload score (30 points) - prefer less loaded counselors
            workload = current_loads.get(counselor["user_id"], 0)
            max_workload = max(current_loads.values()) if current_loads else 1
            workload_score = 30 * (1 - (workload / max(max_workload, 1)))
            score += workload_score
            reasoning.append(f"Workload: {workload} leads ({workload_score:.1f} pts)")
            
            # Specialization score (30 points)
            spec_score = 0
            if lead.country and lead.country in counselor["specialization"]["countries"]:
                spec_score += 15
                reasoning.append(f"Country match: {lead.country} (+15 pts)")
            if lead.interested_course and lead.interested_course in counselor["specialization"]["courses"]:
                spec_score += 15
                reasoning.append(f"Course match: {lead.interested_course} (+15 pts)")
            score += spec_score
            
            # Performance score (25 points)
            perf = counselor["performance"]
            perf_score = min(25, perf["conversion_rate"] * 25)
            score += perf_score
            reasoning.append(f"Conversion rate: {perf['conversion_rate']:.0%} ({perf_score:.1f} pts)")
            
            # Lead score bonus (15 points) - high performers get hot leads
            if lead.ai_score and lead.ai_score >= 80 and perf["conversion_rate"] >= 0.5:
                score += 15
                reasoning.append("Hot lead bonus (+15 pts)")
            
            scored_counselors.append({
                **counselor,
                "score": score,
                "reasoning": " | ".join(reasoning)
            })
        
        # Return highest scoring counselor
        best = max(scored_counselors, key=lambda x: x["score"])
        return best
    
    def _round_robin_assignment(self, counselors: List[Dict]) -> Dict:
        """Simple round-robin with load balancing"""
        current_loads = self._get_current_workloads([c["user_id"] for c in counselors])
        
        # Select counselor with minimum current load
        counselor = min(counselors, key=lambda c: current_loads.get(c["user_id"], 0))
        counselor["reasoning"] = f"Round-robin: {current_loads.get(counselor['user_id'], 0)} current leads"
        
        return counselor
    
    def _skill_based_assignment(
        self,
        lead: Lead,
        counselors: List[Dict],
        current_loads: Optional[Dict[str, int]] = None
    ) -> Dict:
        """Assignment based purely on country/course specialization"""
        if current_loads is None:
            current_loads = self._get_current_workloads([c["user_id"] for c in counselors])
        
        # Filter specialists
        specialists = [
            c for c in counselors
            if (lead.country in c["specialization"]["countries"] or
                lead.interested_course in c["specialization"]["courses"])
        ]
        
        # If no specialists, fall back to all counselors
        pool = specialists if specialists else counselors
        
        # Among specialists, pick least loaded
        counselor = min(pool, key=lambda c: current_loads.get(c["user_id"], 0))
        
        match_type = "specialist" if specialists else "generalist"
        counselor["reasoning"] = f"{match_type} - {current_loads.get(counselor['user_id'], 0)} current leads"
        
        return counselor
    
    def _get_current_workloads(self, counselor_ids: List[str]) -> Dict[str, int]:
        """Get current active lead count per counselor"""
        workloads = self.db.query(
            Lead.assigned_to,
            func.count(Lead.id).label("count")
        ).filter(
            Lead.assigned_to.in_(counselor_ids),
            Lead.status.in_(["new", "contacted", "qualified", "hot", "warm", "cold"])
        ).group_by(Lead.assigned_to).all()
        
        return {user_id: count for user_id, count in workloads}
    
    def _get_performance_score(self, counselor_id: str) -> Dict:
        """Calculate counselor performance metrics"""
        # Get total leads assigned
        total = self.db.query(func.count(Lead.id)).filter(
            Lead.assigned_to == counselor_id
        ).scalar() or 1
        
        # Get converted leads
        converted = self.db.query(func.count(Lead.id)).filter(
            Lead.assigned_to == counselor_id,
            Lead.status == "enrolled"
        ).scalar() or 0
        
        # Get average response time (could be computed from activities)
        # Placeholder for now
        avg_response_time = 2.5  # hours
        
        return {
            "total_leads": total,
            "converted_leads": converted,
            "conversion_rate": converted / max(total, 1),
            "avg_response_time_hours": avg_response_time
        }
    
    def _is_working_hours(self, counselor: User) -> bool:
        """
        Check if counselor is currently in working hours
        Assumes 9 AM - 6 PM in counselor's timezone
        """
        # Get counselor timezone (default to UTC if not set)
        tz_str = getattr(counselor, "timezone", "UTC")
        try:
            tz = pytz.timezone(tz_str)
        except:
            tz = pytz.UTC
        
        # Get current time in counselor's timezone
        now = datetime.now(tz)
        hour = now.hour
        
        # Working hours: 9 AM - 6 PM
        # Skip this check for now - can be enabled later
        # return 9 <= hour < 18
        return True  # Allow 24/7 for now


def get_assignment_strategies() -> List[Dict]:
    """Get available assignment strategies with descriptions"""
    return [
        {
            "id": "intelligent",
            "name": "Intelligent (AI-Driven)",
            "description": "Balances workload, specialization, performance, and lead score",
            "recommended": True,
            "factors": ["Workload (30%)", "Specialization (30%)", "Performance (25%)", "Lead Score (15%)"]
        },
        {
            "id": "round-robin",
            "name": "Round-Robin (Equal Distribution)",
            "description": "Distributes leads equally among all counselors",
            "recommended": False,
            "factors": ["Current workload only"]
        },
        {
            "id": "skill-based",
            "name": "Skill-Based (Specialization)",
            "description": "Matches leads to counselors by country/course expertise",
            "recommended": False,
            "factors": ["Country specialization", "Course specialization", "Workload (tiebreaker)"]
        }
    ]
