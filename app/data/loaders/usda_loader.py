import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class USDALoader: 
    """Loader for USDA food databases"""
    
    @staticmethod
    def load_foundation(filepath: str) -> Dict[str, Any]: 
        """Load USDA Foundation Foods database"""
        try: 
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Your file uses 'FoundationFoods' key
            if isinstance(data, dict):
                foods = data.get('FoundationFoods', data.get('foods', []))
            elif isinstance(data, list):
                foods = data
            else:
                foods = []
            
            logger.info(f"Loaded {len(foods)} foods from Foundation database")
            return {"foods": foods}
            
        except FileNotFoundError: 
            logger.error(f"Foundation file not found: {filepath}")
            return {"foods": []}
        except Exception as e:
            logger.error(f"Error loading Foundation data: {e}")
            return {"foods":  []}
    
    @staticmethod
    def load_sr_legacy(filepath:  str) -> Dict[str, Any]: 
        """Load USDA SR Legacy database"""
        try: 
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Your file uses 'SRLegacyFoods' key
            if isinstance(data, dict):
                foods = data.get('SRLegacyFoods', data.get('foods', []))
            elif isinstance(data, list):
                foods = data
            else: 
                foods = []
            
            logger.info(f"Loaded {len(foods)} foods from SR Legacy database")
            return {"foods": foods}
            
        except FileNotFoundError: 
            logger.error(f"SR Legacy file not found: {filepath}")
            return {"foods": []}
        except Exception as e:
            logger.error(f"Error loading SR Legacy data: {e}")
            return {"foods":  []}