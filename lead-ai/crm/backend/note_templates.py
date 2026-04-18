"""
Note Templates System
Provides pre-configured note templates with variable substitution
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
import re

class NoteTemplates:
    """Manage note templates with variable substitution"""
    
    # Default system templates
    DEFAULT_TEMPLATES = [
        {
            "id": "not_answering",
            "name": "Not Answering",
            "category": "Follow-up",
            "content": "📞 Called {{lead_name}} at {{time}}. No response. Will try again {{next_attempt}}.",
            "variables": ["lead_name", "time", "next_attempt"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "interested_scholarship",
            "name": "Interested in Scholarship",
            "category": "Interest",
            "content": "💰 {{lead_name}} expressed interest in scholarship opportunities for {{course}}. Budget constraint: {{budget}}. Next step: Send scholarship brochure.",
            "variables": ["lead_name", "course", "budget"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "price_concern",
            "name": "Price Concern",
            "category": "Objection",
            "content": "💵 {{lead_name}} mentioned price is a concern for {{course}}. Competitor mentioned: {{competitor}}. Offered: {{offer}}. Need to follow up with manager approval.",
            "variables": ["lead_name", "course", "competitor", "offer"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "request_callback",
            "name": "Requested Callback",
            "category": "Follow-up",
            "content": "📱 {{lead_name}} requested callback at {{preferred_time}} ({{timezone}}). Reason: {{reason}}. Set reminder.",
            "variables": ["lead_name", "preferred_time", "timezone", "reason"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "enrolled_success",
            "name": "Successfully Enrolled",
            "category": "Success",
            "content": "🎉 {{lead_name}} enrolled in {{course}}! Payment: {{payment_amount}} ({{payment_method}}). Start date: {{start_date}}. Welcome email sent.",
            "variables": ["lead_name", "course", "payment_amount", "payment_method", "start_date"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "demo_scheduled",
            "name": "Demo Scheduled",
            "category": "Meeting",
            "content": "📅 Demo scheduled with {{lead_name}} for {{course}} on {{demo_date}} at {{demo_time}}. Platform: {{platform}}. Calendar invite sent.",
            "variables": ["lead_name", "course", "demo_date", "demo_time", "platform"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "needs_documents",
            "name": "Documents Required",
            "category": "Follow-up",
            "content": "📄 {{lead_name}} needs to submit: {{documents_list}}. Deadline: {{deadline}}. Sent checklist via {{channel}}.",
            "variables": ["lead_name", "documents_list", "deadline", "channel"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "parent_decision",
            "name": "Waiting for Parent Decision",
            "category": "Follow-up",
            "content": "👨‍👩‍👧 {{lead_name}} needs parent approval for {{course}}. Parent name: {{parent_name}}. Discussion points: {{concerns}}. Follow up in {{days}} days.",
            "variables": ["lead_name", "course", "parent_name", "concerns", "days"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "visa_query",
            "name": "Visa Related Query",
            "category": "Documentation",
            "content": "🛂 {{lead_name}} asked about visa process for {{country}}. Current status: {{visa_status}}. Documents needed: {{documents}}. Referred to visa team.",
            "variables": ["lead_name", "country", "visa_status", "documents"],
            "is_system": True,
            "usage_count": 0
        },
        {
            "id": "competitor_comparison",
            "name": "Comparing with Competitor",
            "category": "Objection",
            "content": "⚖️ {{lead_name}} comparing us with {{competitor}} for {{course}}. Their concerns: {{concerns}}. Our advantages highlighted: {{advantages}}. Next step: {{next_step}}.",
            "variables": ["lead_name", "competitor", "course", "concerns", "advantages", "next_step"],
            "is_system": True,
            "usage_count": 0
        }
    ]
    
    def __init__(self, templates_file="note_templates.json"):
        self.templates_file = templates_file
        self.templates = self._load_templates()
    
    def _load_templates(self) -> List[Dict]:
        """Load templates from file or use defaults"""
        try:
            with open(self.templates_file, 'r') as f:
                custom_templates = json.load(f)
                # Merge with defaults
                all_templates = self.DEFAULT_TEMPLATES.copy()
                
                # Add custom templates
                for template in custom_templates:
                    if not template.get('is_system'):
                        all_templates.append(template)
                
                return all_templates
        except FileNotFoundError:
            # Return defaults if file doesn't exist
            return self.DEFAULT_TEMPLATES.copy()
    
    def _save_templates(self):
        """Save templates to file"""
        # Only save custom templates (not system templates)
        custom_templates = [t for t in self.templates if not t.get('is_system')]
        
        try:
            with open(self.templates_file, 'w') as f:
                json.dump(custom_templates, f, indent=2)
        except Exception as e:
            print(f"Error saving templates: {e}")
    
    def get_all_templates(self, category: Optional[str] = None) -> List[Dict]:
        """Get all templates, optionally filtered by category"""
        if category:
            return [t for t in self.templates if t.get('category') == category]
        return self.templates
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """Get specific template by ID"""
        for template in self.templates:
            if template.get('id') == template_id:
                return template
        return None
    
    def create_template(self, name: str, content: str, category: str = "Custom") -> Dict:
        """Create new custom template"""
        # Extract variables from content ({{variable_name}})
        variables = re.findall(r'\{\{(\w+)\}\}', content)
        
        template = {
            "id": f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "category": category,
            "content": content,
            "variables": list(set(variables)),
            "is_system": False,
            "usage_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        self.templates.append(template)
        self._save_templates()
        
        return template
    
    def update_template(self, template_id: str, updates: Dict) -> Optional[Dict]:
        """Update existing template"""
        for i, template in enumerate(self.templates):
            if template.get('id') == template_id:
                # Don't allow updating system templates
                if template.get('is_system'):
                    return None
                
                # Update fields
                template.update(updates)
                
                # Re-extract variables if content changed
                if 'content' in updates:
                    variables = re.findall(r'\{\{(\w+)\}\}', updates['content'])
                    template['variables'] = list(set(variables))
                
                template['updated_at'] = datetime.now().isoformat()
                self.templates[i] = template
                self._save_templates()
                
                return template
        
        return None
    
    def delete_template(self, template_id: str) -> bool:
        """Delete custom template"""
        for i, template in enumerate(self.templates):
            if template.get('id') == template_id:
                # Don't allow deleting system templates
                if template.get('is_system'):
                    return False
                
                del self.templates[i]
                self._save_templates()
                return True
        
        return False
    
    def render_template(self, template_id: str, variables: Dict) -> Optional[str]:
        """Render template with variable substitution"""
        template = self.get_template_by_id(template_id)
        if not template:
            return None
        
        content = template['content']
        
        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, str(var_value))
        
        # Increment usage count
        template['usage_count'] = template.get('usage_count', 0) + 1
        self._save_templates()
        
        return content
    
    def get_available_variables(self, lead_data: Dict, user_data: Dict) -> Dict:
        """Get all available variables for substitution"""
        from datetime import datetime
        
        variables = {
            # Lead variables
            "lead_name": lead_data.get("name", ""),
            "lead_email": lead_data.get("email", ""),
            "lead_phone": lead_data.get("phone", ""),
            "course": lead_data.get("course_interested", ""),
            "country": lead_data.get("preferred_country", ""),
            "ai_score": str(lead_data.get("ai_score", "")),
            "status": lead_data.get("status", ""),
            
            # Counselor variables
            "counselor_name": user_data.get("name", ""),
            "counselor_email": user_data.get("email", ""),
            
            # Time variables
            "time": datetime.now().strftime("%I:%M %p"),
            "date": datetime.now().strftime("%B %d, %Y"),
            "today": datetime.now().strftime("%A, %B %d"),
            
            # Common placeholders
            "next_attempt": "tomorrow",
            "preferred_time": "",
            "timezone": "",
            "budget": "",
            "competitor": "",
            "offer": "",
            "reason": "",
            "payment_amount": "",
            "payment_method": "",
            "start_date": "",
            "demo_date": "",
            "demo_time": "",
            "platform": "",
            "documents_list": "",
            "deadline": "",
            "channel": "email",
            "parent_name": "",
            "concerns": "",
            "days": "3",
            "visa_status": "",
            "documents": "",
            "advantages": "",
            "next_step": ""
        }
        
        return variables
    
    def get_popular_templates(self, limit: int = 5) -> List[Dict]:
        """Get most used templates"""
        sorted_templates = sorted(
            self.templates, 
            key=lambda x: x.get('usage_count', 0), 
            reverse=True
        )
        return sorted_templates[:limit]
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for template in self.templates:
            categories.add(template.get('category', 'Uncategorized'))
        return sorted(list(categories))


# Global instance
note_templates_manager = NoteTemplates()
