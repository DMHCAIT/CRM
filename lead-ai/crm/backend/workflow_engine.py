"""
Status-Change Workflow Automation Engine
Triggers automated actions when lead status changes
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from database import Lead, User, Activity
from logger_config import logger


class WorkflowEngine:
    """Executes automated workflows based on lead status changes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.workflows = self._load_workflows()
    
    def trigger_status_change(
        self,
        lead_id: str,
        old_status: str,
        new_status: str,
        user_id: str
    ) -> Dict:
        """
        Execute workflow when lead status changes
        
        Args:
            lead_id: Lead ID
            old_status: Previous status
            new_status: New status
            user_id: User who triggered the change
            
        Returns:
            Execution results
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        # Get workflows for this status change
        workflows = self._get_workflows_for_status(new_status)
        
        if not workflows:
            logger.info(f"No workflows configured for status: {new_status}")
            return {"executed": 0, "actions": []}
        
        results = {
            "executed": 0,
            "actions": [],
            "errors": []
        }
        
        for workflow in workflows:
            try:
                # Check if conditions match
                if not self._check_conditions(lead, workflow.get("conditions", {})):
                    continue
                
                # Execute actions
                for action in workflow.get("actions", []):
                    action_result = self._execute_action(lead, action, user_id)
                    results["actions"].append(action_result)
                    results["executed"] += 1
                
            except Exception as e:
                logger.error(f"Workflow execution failed for {workflow['name']}: {str(e)}")
                results["errors"].append(f"{workflow['name']}: {str(e)}")
        
        return results
    
    def trigger_custom_event(
        self,
        event_type: str,
        lead_id: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Trigger workflow from custom events (note_added, high_score, etc.)
        
        Args:
            event_type: Event type (note_added, score_changed, etc.)
            lead_id: Lead ID
            user_id: User who triggered
            metadata: Additional event data
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        
        workflows = self._get_workflows_for_event(event_type)
        
        results = {
            "executed": 0,
            "actions": [],
            "errors": []
        }
        
        for workflow in workflows:
            try:
                if not self._check_conditions(lead, workflow.get("conditions", {}), metadata):
                    continue
                
                for action in workflow.get("actions", []):
                    action_result = self._execute_action(lead, action, user_id)
                    results["actions"].append(action_result)
                    results["executed"] += 1
                
            except Exception as e:
                logger.error(f"Event workflow failed: {str(e)}")
                results["errors"].append(f"{workflow['name']}: {str(e)}")
        
        return results
    
    def _execute_action(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """
        Execute a single workflow action
        
        Supported actions:
        - send_email: Send email template
        - send_whatsapp: Send WhatsApp message
        - schedule_followup: Auto-schedule follow-up
        - create_task: Create task for counselor
        - update_priority: Update lead priority
        - assign_to: Reassign lead
        - webhook: Call external webhook
        """
        action_type = action.get("type")
        
        if action_type == "send_email":
            return self._action_send_email(lead, action, user_id)
        
        elif action_type == "send_whatsapp":
            return self._action_send_whatsapp(lead, action, user_id)
        
        elif action_type == "schedule_followup":
            return self._action_schedule_followup(lead, action, user_id)
        
        elif action_type == "create_task":
            return self._action_create_task(lead, action, user_id)
        
        elif action_type == "update_priority":
            return self._action_update_priority(lead, action, user_id)
        
        elif action_type == "assign_to":
            return self._action_assign_to(lead, action, user_id)
        
        elif action_type == "add_note":
            return self._action_add_note(lead, action, user_id)
        
        elif action_type == "webhook":
            return self._action_webhook(lead, action, user_id)
        
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _action_send_email(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Send email using template"""
        # This would integrate with communication_service
        template = action.get("template", "welcome")
        
        # Log activity
        activity = Activity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type="email_sent",
            description=f"Automated email sent: {template}",
            metadata={"workflow": True, "template": template}
        )
        self.db.add(activity)
        self.db.commit()
        
        logger.info(f"Workflow: Sent email to lead {lead.id} using template {template}")
        
        return {
            "action": "send_email",
            "template": template,
            "status": "queued",
            "lead_id": lead.id
        }
    
    def _action_send_whatsapp(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Send WhatsApp message"""
        template = action.get("template", "follow_up")
        
        activity = Activity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type="whatsapp_sent",
            description=f"Automated WhatsApp sent: {template}",
            metadata={"workflow": True, "template": template}
        )
        self.db.add(activity)
        self.db.commit()
        
        logger.info(f"Workflow: Sent WhatsApp to lead {lead.id} using template {template}")
        
        return {
            "action": "send_whatsapp",
            "template": template,
            "status": "queued",
            "lead_id": lead.id
        }
    
    def _action_schedule_followup(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Auto-schedule follow-up"""
        hours_ahead = action.get("hours_ahead", 24)
        priority = action.get("priority", "P2")
        
        follow_up_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        
        lead.next_follow_up = follow_up_time
        lead.follow_up_priority = priority
        self.db.commit()
        
        logger.info(f"Workflow: Scheduled follow-up for lead {lead.id} at {follow_up_time}")
        
        return {
            "action": "schedule_followup",
            "follow_up_time": follow_up_time.isoformat(),
            "priority": priority,
            "lead_id": lead.id
        }
    
    def _action_create_task(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Create task/reminder for counselor"""
        task_description = action.get("description", "Follow up with lead")
        
        # Create activity as task
        activity = Activity(
            lead_id=lead.id,
            user_id=lead.assigned_to or user_id,
            activity_type="task_created",
            description=task_description,
            metadata={"workflow": True, "task": True}
        )
        self.db.add(activity)
        self.db.commit()
        
        logger.info(f"Workflow: Created task for lead {lead.id}: {task_description}")
        
        return {
            "action": "create_task",
            "description": task_description,
            "assigned_to": lead.assigned_to,
            "lead_id": lead.id
        }
    
    def _action_update_priority(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Update lead priority"""
        new_priority = action.get("priority", "P2")
        
        lead.follow_up_priority = new_priority
        self.db.commit()
        
        logger.info(f"Workflow: Updated priority for lead {lead.id} to {new_priority}")
        
        return {
            "action": "update_priority",
            "priority": new_priority,
            "lead_id": lead.id
        }
    
    def _action_assign_to(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Reassign lead"""
        strategy = action.get("strategy", "intelligent")
        
        # This would integrate with auto_assignment_orchestrator
        logger.info(f"Workflow: Triggering reassignment for lead {lead.id} using {strategy}")
        
        return {
            "action": "assign_to",
            "strategy": strategy,
            "status": "queued",
            "lead_id": lead.id
        }
    
    def _action_add_note(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Add automated note"""
        note_text = action.get("note", "Automated note from workflow")
        
        activity = Activity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type="note",
            description=note_text,
            metadata={"workflow": True, "automated": True}
        )
        self.db.add(activity)
        self.db.commit()
        
        logger.info(f"Workflow: Added note to lead {lead.id}")
        
        return {
            "action": "add_note",
            "note": note_text,
            "lead_id": lead.id
        }
    
    def _action_webhook(self, lead: Lead, action: Dict, user_id: str) -> Dict:
        """Call external webhook"""
        webhook_url = action.get("url")
        
        # This would make HTTP request to webhook
        logger.info(f"Workflow: Calling webhook {webhook_url} for lead {lead.id}")
        
        return {
            "action": "webhook",
            "url": webhook_url,
            "status": "queued",
            "lead_id": lead.id
        }
    
    def _check_conditions(self, lead: Lead, conditions: Dict, metadata: Optional[Dict] = None) -> bool:
        """Check if workflow conditions are met"""
        if not conditions:
            return True
        
        # AI score condition
        if "min_score" in conditions:
            if (lead.ai_score or 0) < conditions["min_score"]:
                return False
        
        if "max_score" in conditions:
            if (lead.ai_score or 100) > conditions["max_score"]:
                return False
        
        # Country condition
        if "countries" in conditions:
            if lead.country not in conditions["countries"]:
                return False
        
        # Course condition
        if "courses" in conditions:
            if lead.interested_course not in conditions["courses"]:
                return False
        
        # Days inactive condition
        if "days_inactive" in conditions:
            if lead.updated_at:
                days_inactive = (datetime.utcnow() - lead.updated_at).days
                if days_inactive < conditions["days_inactive"]:
                    return False
        
        return True
    
    def _get_workflows_for_status(self, status: str) -> List[Dict]:
        """Get workflows configured for a status"""
        return [
            wf for wf in self.workflows
            if wf.get("trigger") == "status_change" and status in wf.get("statuses", [])
        ]
    
    def _get_workflows_for_event(self, event_type: str) -> List[Dict]:
        """Get workflows for custom event type"""
        return [
            wf for wf in self.workflows
            if wf.get("trigger") == "event" and wf.get("event_type") == event_type
        ]
    
    def _load_workflows(self) -> List[Dict]:
        """Load workflow configurations"""
        # Default workflows
        default_workflows = [
            {
                "name": "Hot Lead Follow-up",
                "trigger": "status_change",
                "statuses": ["hot"],
                "conditions": {"min_score": 80},
                "actions": [
                    {"type": "schedule_followup", "hours_ahead": 2, "priority": "P0"},
                    {"type": "add_note", "note": "🔥 Hot lead - prioritized for immediate follow-up"}
                ]
            },
            {
                "name": "Enrollment Welcome",
                "trigger": "status_change",
                "statuses": ["enrolled"],
                "conditions": {},
                "actions": [
                    {"type": "send_email", "template": "welcome_enrolled"},
                    {"type": "send_whatsapp", "template": "payment_reminder"},
                    {"type": "add_note", "note": "✅ Enrolled - welcome email and payment link sent"}
                ]
            },
            {
                "name": "Not Answering Retry",
                "trigger": "status_change",
                "statuses": ["not_answering"],
                "conditions": {},
                "actions": [
                    {"type": "schedule_followup", "hours_ahead": 48, "priority": "P2"},
                    {"type": "add_note", "note": "📞 Not answering - scheduled retry in 2 days"}
                ]
            },
            {
                "name": "Qualified Demo Scheduling",
                "trigger": "status_change",
                "statuses": ["qualified"],
                "conditions": {},
                "actions": [
                    {"type": "schedule_followup", "hours_ahead": 12, "priority": "P0"},
                    {"type": "create_task", "description": "Schedule product demo with qualified lead"},
                    {"type": "update_priority", "priority": "P0"}
                ]
            },
            {
                "name": "Churn Prevention",
                "trigger": "event",
                "event_type": "high_churn_risk",
                "conditions": {"min_score": 60},
                "actions": [
                    {"type": "assign_to", "strategy": "top_performer"},
                    {"type": "send_whatsapp", "template": "retention_offer"},
                    {"type": "update_priority", "priority": "P0"}
                ]
            },
            {
                "name": "Stale Lead Reminder",
                "trigger": "event",
                "event_type": "lead_inactive",
                "conditions": {"days_inactive": 7},
                "actions": [
                    {"type": "create_task", "description": "Follow up with inactive lead"},
                    {"type": "send_whatsapp", "template": "reengagement"}
                ]
            }
        ]
        
        # Try to load custom workflows from file
        try:
            import os
            workflow_file = os.path.join(os.path.dirname(__file__), "status_workflows.json")
            if os.path.exists(workflow_file):
                with open(workflow_file, "r") as f:
                    custom_workflows = json.load(f)
                    logger.info(f"Loaded {len(custom_workflows)} custom workflows")
                    return custom_workflows
        except Exception as e:
            logger.warning(f"Could not load custom workflows: {str(e)}")
        
        return default_workflows
    
    def get_workflow_definitions(self) -> List[Dict]:
        """Get all workflow definitions for UI display"""
        return self.workflows
    
    def save_workflow(self, workflow: Dict) -> bool:
        """Save or update workflow definition"""
        try:
            import os
            
            # Load existing workflows
            workflow_file = os.path.join(os.path.dirname(__file__), "status_workflows.json")
            
            if os.path.exists(workflow_file):
                with open(workflow_file, "r") as f:
                    workflows = json.load(f)
            else:
                workflows = []
            
            # Update or append
            existing_idx = next(
                (i for i, wf in enumerate(workflows) if wf.get("name") == workflow.get("name")),
                None
            )
            
            if existing_idx is not None:
                workflows[existing_idx] = workflow
            else:
                workflows.append(workflow)
            
            # Save
            with open(workflow_file, "w") as f:
                json.dump(workflows, f, indent=2)
            
            # Reload
            self.workflows = workflows
            
            logger.info(f"Saved workflow: {workflow.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save workflow: {str(e)}")
            return False
