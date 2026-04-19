"""
AI Assistant Module - Claude Integration (Anthropic)
Provides intelligent features using Claude instead of GPT-4
"""

import os
from typing import List, Dict, Optional, Any
from anthropic import Anthropic
from dotenv import load_dotenv
from logger_config import logger
import json

load_dotenv()

class AIAssistant:
    """Claude-powered AI assistant for CRM operations"""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"  # Latest Claude model
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info("✅ Claude (Anthropic) client initialized", extra={"system": "ai"})
            except Exception as e:
                logger.error(f"❌ Claude initialization failed: {e}", extra={"system": "ai"})
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY not found - AI features disabled", extra={"system": "ai"})
    
    def is_available(self) -> bool:
        """Check if AI assistant is available"""
        return self.client is not None
    
    async def natural_language_search(self, query: str, leads: List[Dict]) -> List[Dict]:
        """
        Search leads using natural language queries
        
        Example queries:
        - "Show me all hot leads from India who are interested in MBBS"
        - "Find leads that haven't been contacted in 7 days"
        - "Which leads have high conversion probability but low engagement?"
        """
        
        if not self.is_available():
            logger.warning("AI search unavailable, returning all leads", extra={"system": "ai"})
            return leads[:10]
        
        try:
            # Prepare lead data context
            leads_summary = [
                {
                    "id": lead.get("id"),
                    "name": lead.get("full_name"),
                    "status": lead.get("status"),
                    "score": lead.get("ai_score"),
                    "country": lead.get("country"),
                    "course": lead.get("course_interested"),
                    "source": lead.get("source"),
                    "created": str(lead.get("created_at", ""))[:10]
                }
                for lead in leads[:100]  # Limit context
            ]
            
            prompt = f"""You are a CRM search assistant. Analyze this query and return matching lead IDs.

Query: {query}

Available leads (JSON):
{json.dumps(leads_summary, indent=2)}

Return ONLY a JSON array of matching lead IDs. Example: ["id1", "id2", "id3"]
If no matches, return empty array: []"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            matched_ids = json.loads(response_text)
            
            # Filter leads
            result = [lead for lead in leads if lead.get("id") in matched_ids]
            
            logger.info(f"NL search: '{query}' → {len(result)} matches", extra={"system": "ai"})
            return result
            
        except Exception as e:
            logger.error(f"NL search failed: {e}", extra={"system": "ai"})
            return leads[:10]
    
    async def generate_reply_suggestion(self, lead_data: Dict, message_type: str = "email") -> str:
        """
        Generate smart reply suggestions for WhatsApp/Email
        
        Args:
            lead_data: Lead information
            message_type: "email" or "whatsapp"
        """
        
        if not self.is_available():
            return f"Hi {lead_data.get('full_name', 'there')}, thank you for your interest..."
        
        try:
            prompt = f"""Generate a professional {message_type} message for this lead:

Lead: {lead_data.get('full_name')}
Status: {lead_data.get('status')}
Course: {lead_data.get('course_interested')}
Country: {lead_data.get('country')}
AI Score: {lead_data.get('ai_score')}/100

Write a personalized, friendly message (max 150 words). Include:
- Greeting
- Reference to their interest
- Call to action
- Professional tone

Return ONLY the message text, no explanations."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Reply generation failed: {e}", extra={"system": "ai"})
            return f"Hi {lead_data.get('full_name')}, thank you for your interest in {lead_data.get('course_interested')}. We'd love to discuss your options!"
    
    async def summarize_notes(self, notes: List[str]) -> str:
        """Generate a concise summary of lead notes"""
        
        if not self.is_available() or not notes:
            return "No notes available"
        
        try:
            notes_text = "\n\n".join([f"- {note}" for note in notes[:20]])
            
            prompt = f"""Summarize these CRM notes into 2-3 key bullet points:

{notes_text}

Format: Simple bullet points, max 100 words total."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Note summarization failed: {e}", extra={"system": "ai"})
            return "Summary unavailable"
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of lead communication"""
        
        if not self.is_available():
            return {"sentiment": "neutral", "score": 0.5, "keywords": []}
        
        try:
            prompt = f"""Analyze the sentiment of this message:

"{text}"

Return ONLY valid JSON:
{{
  "sentiment": "positive|neutral|negative",
  "score": 0.0-1.0,
  "keywords": ["word1", "word2"]
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return json.loads(message.content[0].text.strip())
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}", extra={"system": "ai"})
            return {"sentiment": "neutral", "score": 0.5, "keywords": []}


# Singleton instance
ai_assistant = AIAssistant()
