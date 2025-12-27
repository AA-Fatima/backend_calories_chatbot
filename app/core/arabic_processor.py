import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ArabicProcessor:
    """Process Arabic text using translation - NO HARDCODING!"""
    
    def __init__(self):
        self.translator = None
        self._init_translator()
    
    def _init_translator(self):
        """Initialize Arabic to English translator"""
        try:
            from deep_translator import GoogleTranslator
            self.translator = GoogleTranslator(source='ar', target='en')
            logger.info("Arabic translator ready - can translate ANY Arabic text!")
        except ImportError:
            logger.error("deep-translator not installed!")
            self.translator = None
        except Exception as e: 
            logger.error(f"Translator init failed: {e}")
            self.translator = None
    
    def is_arabic(self, text:  str) -> bool:
        """Check if text contains Arabic characters"""
        return bool(re.search(r'[\u0600-\u06FF]', text))
    
    def normalize(self, text:  str) -> str:
        """Normalize Arabic text (remove diacritics, standardize letters)"""
        # Remove diacritics (tashkeel)
        text = re.sub(r'[\u064B-\u0652]', '', text)
        # Normalize alef variations
        text = re.sub(r'[إأآا]', 'ا', text)
        # Normalize taa marbuta
        text = text.replace('ة', 'ه')
        # Normalize yaa
        text = text.replace('ى', 'ي')
        return text
    
    def translate_food_terms(self, text: str) -> str:
        """Translate ANY Arabic text to English"""
        if not self.is_arabic(text):
            return text
        
        if not self.translator:
            logger.warning("No translator available")
            return text
        
        try:
            # Translate the entire text
            result = self.translator.translate(text)
            logger.debug(f"Arabic translation: '{text}' -> '{result}'")
            return result if result else text
        except Exception as e: 
            logger.warning(f"Translation failed: {e}")
            return text