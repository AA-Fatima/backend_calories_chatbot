import re
import logging
from typing import Optional
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class FrankoConverter:
    """Convert ANY Franco-Arabic or Arabic to English using translation APIs"""
    
    def __init__(self):
        self.translator = None
        self._init_translator()
        
        # Only map Franco numbers to letters (this is standard, not hardcoding)
        self.number_map = {
            "2": "a",
            "3":  "a", 
            "5": "kh",
            "6": "t",
            "7": "h",
            "8": "q",
            "9": "s",
        }
    
    def _init_translator(self):
        """Initialize Google Translator"""
        try: 
            from deep_translator import GoogleTranslator
            self.translator = GoogleTranslator(source='auto', target='en')
            logger.info("Google Translator initialized - can translate ANY language!")
        except ImportError:
            logger.error("deep-translator not installed!  Run: pip install deep-translator")
            self.translator = None
        except Exception as e: 
            logger.error(f"Could not initialize translator: {e}")
            self.translator = None
    
    def is_franco(self, text: str) -> bool:
        """Check if text contains Franco-Arabic (Arabic written in Latin + numbers)"""
        has_latin = bool(re.search(r'[a-zA-Z]', text))
        has_franco_numbers = bool(re.search(r'[2357]', text))
        return has_latin and has_franco_numbers
    
    def is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        return bool(re.search(r'[\u0600-\u06FF]', text))
    
    def detect_language(self, text: str) -> str:
        """Detect language automatically"""
        if self.is_arabic(text):
            return "arabic"
        if self.is_franco(text):
            return "franco"
        
        try:
            lang = detect(text)
            return lang
        except LangDetectException: 
            return "en"
    
    def convert(self, text: str) -> str:
        """Convert ANY text to searchable English"""
        original_text = text.strip()
        
        # Step 1: Convert Franco numbers to letters
        converted = original_text.lower()
        for num, letter in self.number_map.items():
            converted = converted.replace(num, letter)
        
        # Step 2: If text has Arabic OR was Franco, translate to English
        if self.is_arabic(original_text) or self.is_franco(original_text):
            translated = self.translate_to_english(converted)
            if translated:
                converted = translated.lower()
        
        # Clean up
        converted = ' '.join(converted.split())
        return converted.strip()
    
    def translate_to_english(self, text: str) -> Optional[str]:
        """Translate ANY text to English using Google Translate"""
        if not self.translator:
            logger.warning("Translator not available")
            return text
        
        try:
            # Google Translate auto-detects language and translates
            result = self.translator.translate(text)
            logger.debug(f"Translated '{text}' -> '{result}'")
            return result
        except Exception as e:
            logger.warning(f"Translation failed for '{text}': {e}")
            return text