import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.models.schemas import Intent, ParsedQuery
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class NLPEngine:
    """Advanced NLP engine - translates ONLY Arabic script, not Latin text! """
    
    def __init__(self):
        self.translator = None
        self.semantic_model = None
        self.spell_checker = None
        self.initialized = False
        self.food_vocabulary = self._build_food_vocabulary()
        
        self._init_translator()
        self._init_semantic_model()
        self._init_spell_checker()
    
    def _init_translator(self):
        """Initialize Google Translator for Arabic ONLY"""
        try:
            from deep_translator import GoogleTranslator
            # Only translate from Arabic to English
            self.translator = GoogleTranslator(source='ar', target='en')
            logger.info("✅ Arabic translator initialized")
        except Exception as e:
            logger.warning(f"Translator not available: {e}")
            self.translator = None
    
    def _init_semantic_model(self):
        """Initialize semantic similarity model"""
        try: 
            from sentence_transformers import SentenceTransformer
            self.semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✅ Semantic model initialized")
        except Exception as e: 
            logger.warning(f"Semantic model not available: {e}")
            self.semantic_model = None
    
    def _init_spell_checker(self):
        """Initialize spell checker for typo correction"""
        try:
            # Spell checker is using rapidfuzz which is already in requirements
            self.spell_checker = True
            logger.info("✅ Spell checker initialized")
        except Exception as e:
            logger.warning(f"Spell checker not available: {e}")
            self.spell_checker = None
    
    def _build_food_vocabulary(self) -> Dict[str, List[str]]:
        """Build vocabulary of common food names and their misspellings"""
        return {
            # Common dishes and variations
            "shawarma": ["shawerma", "shawrma", "sha2arma", "shawerma", "shwarma", "shawarmaa"],
            "falafel": ["falafil", "felafel", "flafel", "falefel"],
            "kabsa": ["kabseh", "kabsah", "kapsa", "kabseh"],
            "kushari": ["koshary", "koshari", "kushari", "kosheri"],
            "fajita": ["fahita", "fajitas", "fajetas"],
            "biryani": ["biriani", "biryanii", "briyani"],
            "hummus": ["humus", "hommus", "houmous"],
            "tabouleh": ["tabbouleh", "tabouli", "tabbouli"],
            "kibbeh": ["kibbe", "kebbeh", "kebeh"],
            
            # Common ingredients  
            "chicken": ["chiken", "chickin", "chikn", "chcken"],
            "rice": ["rize", "riice"],
            "tomato": ["tomatoe", "tomatos"],
            "potato": ["potatoe", "potatos", "pototo"],
            "onion": ["onian", "onoin"],
            "garlic": ["garlik", "garlick"],
            "bread": ["bred", "berad"],
            "cheese": ["chees", "cheez", "chese"],
            "yogurt": ["yoghurt", "yogourt", "yoghourt"],
            "cucumber": ["cucmber", "cucumbr"],
            "lettuce": ["letuce", "lettuse"],
            "apple": ["aple", "appel"],
            "banana": ["bananna", "bannana"],
            "orange": ["orang", "orenge"],
        }
    
    def _correct_spelling(self, text: str) -> str:
        """Correct common food name typos using fuzzy matching"""
        if not self.spell_checker:
            return text
        
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        # Check each word for correction
        corrected_words = []
        for word in words:
            corrected = word
            best_score = 0
            
            # Check against vocabulary
            for correct_word, variations in self.food_vocabulary.items():
                # Check if word matches any variation
                if word == correct_word:
                    corrected = correct_word
                    break
                elif word in variations:
                    corrected = correct_word
                    break
                else:
                    # Use fuzzy matching for typos
                    from rapidfuzz import fuzz
                    score = fuzz.ratio(word, correct_word)
                    if score > 80 and score > best_score:
                        best_score = score
                        corrected = correct_word
                    
                    # Also check against variations
                    for variation in variations:
                        score = fuzz.ratio(word, variation)
                        if score > 90 and score > best_score:
                            best_score = score
                            corrected = correct_word
            
            corrected_words.append(corrected)
        
        result = ' '.join(corrected_words)
        if result != text_lower:
            logger.info(f"Spell corrected: '{text_lower}' -> '{result}'")
        return result
    
    async def initialize(self):
        """Initialize NLP engine"""
        self.initialized = True
        logger.info("NLP Engine fully initialized")
    
    def parse_query(self, text: str, context: Optional[Dict] = None) -> ParsedQuery: 
        """Parse user query"""
        
        # Step 1: Detect if text contains Arabic script
        has_arabic = self._has_arabic_script(text)
        
        # Step 2: Normalize text (only translate if Arabic)
        normalized_text = self._normalize_text(text, has_arabic)
        logger.info(f"Normalized:  '{text}' -> '{normalized_text}'")
        
        # Step 3: Correct spelling for common typos
        corrected_text = self._correct_spelling(normalized_text)
        if corrected_text != normalized_text:
            logger.info(f"Spell corrected: '{normalized_text}' -> '{corrected_text}'")
            normalized_text = corrected_text
        
        # Step 4: Detect language for response
        language = "arabic" if has_arabic else self._detect_language(text)
        
        # Step 5: Classify intent
        intent = self._classify_intent(normalized_text, context)
        
        # Step 6: Extract food items
        food_items = self._extract_food_items(normalized_text)
        
        # Step 7: Extract modifications
        modifications = self._extract_modifications(normalized_text)
        
        # Step 8: Extract quantities
        quantities = self._extract_quantities(normalized_text)
        
        # Step 9: Calculate confidence score
        confidence = self._calculate_confidence(normalized_text, food_items, intent)
        
        return ParsedQuery(
            intent=intent,
            food_items=food_items,
            modifications=modifications,
            quantities=quantities,
            language_detected=language,
            original_text=text,
            normalized_text=normalized_text,
            confidence=confidence
        )
    
    def _has_arabic_script(self, text:  str) -> bool:
        """Check if text contains Arabic script characters"""
        return bool(re.search(r'[\u0600-\u06FF]', text))
    
    def _is_franco_arabic(self, text: str) -> bool:
        """Check if text is Franco-Arabic (Latin + numbers like 7, 3, 2)"""
        has_latin = bool(re.search(r'[a-zA-Z]', text))
        has_franco_numbers = bool(re.search(r'[2357]', text))
        return has_latin and has_franco_numbers
    
    def _detect_language(self, text: str) -> str:
        """Detect language"""
        if self._has_arabic_script(text):
            return "arabic"
        if self._is_franco_arabic(text):
            return "franco"
        return "english"
    
    def _normalize_text(self, text: str, has_arabic: bool) -> str:
        """
        Normalize text: 
        - If Arabic script: translate to English
        - If Latin text (English/Franco): just clean it, DON'T translate! 
        """
        result = text.strip()
        
        # ONLY translate if text has Arabic script
        if has_arabic and self.translator:
            try:
                # Extract and translate only Arabic parts
                translated = self.translator.translate(result)
                if translated: 
                    result = translated
                    logger.info(f"Translated Arabic:  '{text}' -> '{result}'")
            except Exception as e: 
                logger.warning(f"Translation failed: {e}")
        
        # Convert to lowercase
        result = result.lower()
        
        # Handle Franco-Arabic numbers (for Franco text) - Improved mapping
        if self._is_franco_arabic(text) or any(char in result for char in '23578'):
            franco_numbers = {
                '2': 'aa',  # More accurate: hamza/glottal stop → aa
                '3': 'aa',  # 'ayn → aa
                '5': 'kh',  # kha
                '6': 't',   # ta
                '7': 'h',   # ha
                '8': 'gh',  # ghain
                '9': 'q'    # qaf (sometimes 's' for sad)
            }
            for num, letter in franco_numbers.items():
                result = result.replace(num, letter)
            logger.info(f"Franco converted: '{text}' -> '{result}'")
        
        # Clean up spaces
        result = ' '.join(result.split())
        
        return result.strip()
    
    def _classify_intent(self, text: str, context:  Optional[Dict] = None) -> Intent:
        """Classify intent"""
        text_lower = text.lower()
        
        # Greeting patterns
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good evening', 'marhaba', 'ahlan', 'salam']
        if any(text_lower.strip() == g or text_lower.startswith(g + ' ') for g in greetings):
            return Intent.GREETING
        
        # Help patterns
        if any(word in text_lower for word in ['help', 'how do', 'how to', 'what can']):
            return Intent.HELP
        
        # Remove patterns
        remove_words = ['without', 'remove', 'no ', 'except', 'minus', 'exclude', 'hold the', 'bala', 'bidun', 'bidoun']
        if any(word in text_lower for word in remove_words):
            return Intent.MODIFY_REMOVE
        
        # Add patterns
        add_words = ['extra', 'add ', 'plus', 'include', 'with ']
        if any(word in text_lower for word in add_words):
            return Intent.MODIFY_ADD
        
        return Intent.QUERY_FOOD
    
    def _extract_food_items(self, text: str) -> List[str]:
        """Extract food items from text - improved for messy inputs"""
        text_lower = text.lower().strip()
        
        # Clean up common question patterns first
        question_patterns = [
            'how many cal in', 'how many calories in', 'how many calories',
            'what are the calories', 'calories in', 'calories of', 'calories for',
            'calorie count', 'what is', 'tell me about', 'i want', 'i need',
            'give me', 'can i have', 'please', 'thanks', 'thank you'
        ]
        for pattern in question_patterns:
            text_lower = text_lower.replace(pattern, ' ')
        
        # Handle modification patterns first
        modification_patterns = [
            ' without ', ' bala ', ' bidun ', ' bidoun ',
            ' with ', ' plus ', ' add ', ' extra ',
            ' remove ', ' minus ', ' no '
        ]
        
        for pattern in modification_patterns: 
            if pattern in ' ' + text_lower + ' ':
                food_part = text_lower.split(pattern.strip())[0].strip()
                food_part = self._clean_food_name(food_part)
                if food_part:
                    return [food_part]
        
        # Clean and return
        cleaned = self._clean_food_name(text_lower)
        if not cleaned:
            # If cleaning removed everything, try to extract any meaningful words
            words = text_lower.split()
            skip_words = {'the', 'a', 'an', 'in', 'of', 'for', 'calories', 'calorie', 'kcal', 'cal', 'how', 'many', 'much'}
            meaningful = [w for w in words if w not in skip_words and len(w) > 2]
            if meaningful:
                cleaned = ' '.join(meaningful)
        
        return [cleaned] if cleaned else [text_lower]
    
    def _clean_food_name(self, text: str) -> str:
        """Remove question words and common phrases"""
        remove_phrases = [
            'how many calories in', 'how many calories', 'what are the calories',
            'calories in', 'calories of', 'calories for', 'calorie count',
            'what is', 'tell me about', 'i want', 'i need', 'give me',
            'can i have', 'please', 'thanks', 'thank you',
            'the ', 'a ', 'an ',
        ]
        
        result = text.lower()
        for phrase in remove_phrases: 
            result = result.replace(phrase, ' ')
        
        # Remove standalone words
        remove_words = ['calories', 'calorie', 'kcal', 'cal']
        words = result.split()
        words = [w for w in words if w not in remove_words]
        
        return ' '.join(words).strip()
    
    def _extract_modifications(self, text: str) -> Dict[str, List[str]]: 
        """Extract modifications"""
        modifications = {"remove": [], "add":  []}
        text_lower = ' ' + text.lower() + ' '
        
        # Remove patterns
        remove_patterns = [' without ', ' bala ', ' bidun ', ' bidoun ', ' remove ', ' minus ', ' no ', ' exclude ']
        
        for pattern in remove_patterns:
            if pattern in text_lower:
                parts = text_lower.split(pattern)
                if len(parts) > 1:
                    after = parts[1].strip()
                    item = self._extract_first_item(after)
                    if item: 
                        modifications["remove"].append(item)
        
        # Add patterns
        add_patterns = [' with added ', ' with extra ', ' extra ', ' add ', ' plus ']
        
        for pattern in add_patterns:
            if pattern in text_lower:
                parts = text_lower.split(pattern)
                if len(parts) > 1:
                    after = parts[1].strip()
                    item = self._extract_first_item(after)
                    if item:
                        modifications["add"].append(item)
        
        return modifications
    
    def _extract_first_item(self, text: str) -> Optional[str]:
        """Extract first meaningful item from text"""
        text = text.strip()
        
        # Handle "30g of X" pattern
        if ' of ' in text: 
            after_of = text.split(' of ', 1)[1]
            words = after_of.split()
            if words:
                return words[0].strip('.,! ?')
        
        # Get first non-quantity word
        words = text.split()
        skip = {'a', 'an', 'the', 'some', 'any', 'g', 'kg', 'gram', 'grams', 'oz', 'cup', 'cups'}
        
        for word in words:
            clean = word.strip('.,!?')
            if clean.isdigit():
                continue
            if any(c.isdigit() for c in clean):
                continue
            if clean in skip:
                continue
            return clean
        
        return None
    
    def _extract_quantities(self, text:  str) -> Dict[str, float]:
        """Extract quantities from text"""
        quantities = {}
        text_lower = text.lower()
        
        # Find weight patterns:  200g, 200 g, 200 grams
        weight_match = re.search(r'(\d+)\s*(g|gram|grams|kg)\b', text_lower)
        if weight_match:
            value = float(weight_match.group(1))
            unit = weight_match.group(2)
            if 'kg' in unit: 
                value *= 1000
            quantities["_weight"] = value
        
        # Multipliers
        if 'double' in text_lower or 'twice' in text_lower:
            quantities["_multiplier"] = 2.0
        elif 'triple' in text_lower: 
            quantities["_multiplier"] = 3.0
        elif 'half' in text_lower: 
            quantities["_multiplier"] = 0.5
        
        return quantities
    
    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using sentence transformers"""
        if not self.semantic_model:
            return self._compute_word_similarity(text1, text2)
        
        try: 
            from sentence_transformers import util
            emb1 = self.semantic_model.encode(text1, convert_to_tensor=True)
            emb2 = self.semantic_model.encode(text2, convert_to_tensor=True)
            similarity = util.cos_sim(emb1, emb2).item()
            return similarity
        except Exception as e:
            logger.debug(f"Semantic similarity failed: {e}")
            return self._compute_word_similarity(text1, text2)
    
    def _compute_word_similarity(self, text1: str, text2: str) -> float:
        """Fallback word overlap similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)
    
    def find_most_similar(self, query: str, candidates: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """Find most similar items using semantic search"""
        if not candidates:
            return []
        
        if self.semantic_model:
            try:
                from sentence_transformers import util
                query_emb = self.semantic_model.encode(query, convert_to_tensor=True)
                candidate_embs = self.semantic_model.encode(candidates, convert_to_tensor=True)
                similarities = util.cos_sim(query_emb, candidate_embs)[0]
                
                results = [(candidates[i], similarities[i].item()) for i in range(len(candidates))]
                results.sort(key=lambda x: x[1], reverse=True)
                return results[:top_k]
            except Exception as e:
                logger.debug(f"Semantic search failed: {e}")
        
        # Fallback to fuzzy matching
        from rapidfuzz import fuzz, process
        matches = process.extract(query, candidates, scorer=fuzz.token_set_ratio, limit=top_k)
        return [(m[0], m[1] / 100.0) for m in matches]
    
    def is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic"""
        return self._has_arabic_script(text)
    
    def is_franco(self, text:  str) -> bool:
        """Check if text is Franco-Arabic"""
        return self._is_franco_arabic(text)
    
    def _calculate_confidence(self, normalized_text: str, food_items: List[str], intent: Intent) -> float:
        """Calculate confidence score for the parsed query"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if we extracted food items
        if food_items and food_items[0]:
            confidence += 0.2
            
            # Even higher if food item is in our vocabulary
            food_text = food_items[0].lower()
            if any(food_text in [key] + vals for key, vals in self.food_vocabulary.items()):
                confidence += 0.2
        
        # Higher confidence for clear intents
        if intent in [Intent.QUERY_FOOD, Intent.MODIFY_REMOVE, Intent.MODIFY_ADD]:
            confidence += 0.1
        
        # Lower confidence for very short queries
        if len(normalized_text.split()) < 2:
            confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))