from typing import Dict, Any, List
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)

class MissingDishLogger:
    """Log missing dishes for later review"""
    
    def __init__(self, log_file: str = "missing_dishes.json"):
        self.log_file = log_file
        self.missing_dishes = self._load_logs()
    
    def _load_logs(self) -> List[Dict]: 
        """Load existing logs"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_logs(self):
        """Save logs to file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.missing_dishes, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving missing dishes log: {e}")
    
    def log(self, query: str, country: str, fallback_response: Dict = None, user_ingredients: List[str] = None):
        """Log a missing dish"""
        entry = {
            "query": query,
            "country": country,
            "timestamp": datetime.utcnow().isoformat(),
            "fallback_response": fallback_response,
            "user_provided_ingredients": user_ingredients,
            "resolved":  False
        }
        
        # Check if already logged
        for dish in self.missing_dishes: 
            if dish["query"].lower() == query.lower() and dish["country"] == country: 
                logger.info(f"Dish already logged: {query}")
                return
        
        self.missing_dishes.append(entry)
        self._save_logs()
        logger.info(f"Logged missing dish:  {query} ({country})")
    
    def get_unresolved(self) -> List[Dict]:
        """Get all unresolved missing dishes"""
        return [d for d in self.missing_dishes if not d["resolved"]]
    
    def mark_resolved(self, query: str, country:  str):
        """Mark a dish as resolved"""
        for dish in self.missing_dishes:
            if dish["query"].lower() == query.lower() and dish["country"] == country: 
                dish["resolved"] = True
        self._save_logs()