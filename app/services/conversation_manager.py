from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

class ConversationManager:
    """Manage conversation context and history"""
    
    def __init__(self):
        self.sessions:  Dict[str, Dict] = {}
    
    def create_session(self, country: str) -> str:
        """Create new conversation session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "country": country,
            "history": [],
            "last_dish": None,
            "last_result": None,
            "awaiting_ingredients": False,
            "created_at": datetime. utcnow()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id:  str, **kwargs):
        """Update session data"""
        if session_id in self. sessions:
            self.sessions[session_id].update(kwargs)
    
    def add_message(self, session_id: str, role: str, content:  str, metadata: Dict = None):
        """Add message to history"""
        if session_id in self. sessions:
            self.sessions[session_id]["history"].append({
                "role": role,
                "content": content,
                "timestamp":  datetime.utcnow().isoformat(),
                "metadata": metadata
            })
    
    def get_context(self, session_id: str) -> Dict[str, Any]: 
        """Get conversation context for NLP"""
        session = self.sessions.get(session_id, {})
        return {
            "country": session.get("country"),
            "last_dish": session. get("last_dish"),
            "last_result": session. get("last_result"),
            "awaiting_ingredients": session.get("awaiting_ingredients", False),
            "history_length": len(session.get("history", []))
        }