from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz, process
import logging

logger = logging.getLogger(__name__)


class FoodSearchService:
    """Food search using fuzzy matching - NO semantic search to avoid wrong results"""
    
    def __init__(
        self,
        usda_foundation:  Any,
        usda_sr_legacy:  Any,
        dishes: Any,
        nlp_engine: Any
    ):
        # Extract foods
        self.usda_foundation = self._get_foods_list(usda_foundation)
        self.usda_sr_legacy = self._get_foods_list(usda_sr_legacy)
        self.dishes = self._get_dishes_list(dishes)
        self.nlp_engine = nlp_engine
        
        logger.info(f"Loaded - Foundation: {len(self.usda_foundation)}, SR Legacy: {len(self.usda_sr_legacy)}, Dishes: {len(self.dishes)}")
        
        # Build search index
        self.search_index = self._build_search_index()
        
        # Separate indices
        self.dish_index = [item for item in self.search_index if item["source"] == "dishes"]
        self.usda_index = [item for item in self.search_index if item["source"] != "dishes"]
        
        # Name lists for fuzzy search
        self.dish_names = [item["name"] for item in self.dish_index]
        self.usda_names = [item["name"] for item in self.usda_index]
        self.all_names = [item["name"] for item in self.search_index]
        
        logger.info(f"Search index:  {len(self.search_index)} total ({len(self.dish_index)} dishes, {len(self.usda_index)} USDA)")
    
    def _get_foods_list(self, data: Any) -> List[Dict]: 
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ['foods', 'FoundationFoods', 'SRLegacyFoods']: 
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    
    def _get_dishes_list(self, data: Any) -> List[Dict]: 
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ['all_dishes', 'dishes']: 
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    
    def _build_search_index(self) -> List[Dict]:
        index = []
        
        for dish in self.dishes:
            name = dish.get("dish_name", "")
            if name:
                index.append({
                    "name": name.lower(),
                    "original_name": name,
                    "data": dish,
                    "source": "dishes",
                    "country": dish.get("country", "").lower()
                })
        
        for food in self.usda_foundation:
            name = food.get("description", "")
            if name:
                index.append({
                    "name":  name.lower(),
                    "original_name": name,
                    "data":  food,
                    "source": "usda_foundation",
                    "country":  ""
                })
        
        for food in self.usda_sr_legacy: 
            name = food.get("description", "")
            if name:
                index.append({
                    "name": name.lower(),
                    "original_name": name,
                    "data": food,
                    "source": "usda_sr_legacy",
                    "country":  ""
                })
        
        return index
    
    def _normalize_item_name(self, name: str) -> List[str]:
        """Normalize item name to list of words for matching"""
        normalized = name.replace(',', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ').lower()
        return [w for w in normalized.split() if w]
    
    def _is_plural_match(self, singular: str, plural: str) -> bool:
        """Check if singular form matches plural form"""
        # Handle common plural patterns
        if plural == singular + 's':  # apple -> apples
            return True
        if plural == singular + 'es':  # tomato -> tomatoes
            return True
        if len(singular) >= 2 and singular[-1] == 'y' and plural == singular[:-1] + 'ies':  # berry -> berries
            return True
        return False
    
    def search(self, query:  str, country: str = "", top_k: int = 5) -> List[Tuple[Dict, str, float]]:
        """Search for food - prioritize USDA for single-word ingredient queries"""
        query_lower = query.lower().strip()
        country_lower = country.lower().strip() if country else ""
        
        if not query_lower: 
            return []
        
        logger.info(f"Searching for:  '{query_lower}' (country: {country_lower})")
        
        # Detect if this is a single-word ingredient query
        is_single_word = len(query_lower.split()) == 1
        logger.info(f"Is single word: {is_single_word}")
        
        # Step 1: Exact match check
        exact_match = None
        for item in self.search_index:
            if query_lower == item["name"]:
                if item["source"] == "dishes":
                    if not country_lower or item["country"] == country_lower:
                        exact_match = [(item["data"], item["source"], 1.0)]
                        break
                else:
                    # Exact USDA match
                    logger.info(f"Exact USDA match: {item['original_name']}")
                    return [(item["data"], item["source"], 1.0)]
        
        # If exact dish match found and NOT a single word, return it
        if exact_match and not is_single_word:
            logger.info(f"Exact dish match: {exact_match[0][0].get('dish_name')}")
            return exact_match
        
        results = []
        
        # Step 2: For single-word queries, search USDA FIRST
        if is_single_word:
            logger.info(f"Single-word query detected, searching USDA first")
            
            # Search USDA ingredients with word-level matching
            word_matches = []
            for item in self.usda_index:
                item_words = self._normalize_item_name(item["name"])
                
                # Calculate base score
                base_score = 0.0
                is_first_word_match = False
                
                # BEST: Query matches the FIRST word exactly OR as plural
                if item_words and item_words[0] == query_lower:
                    base_score = 0.95
                    is_first_word_match = True
                # Handle plural forms: "apple" matches "apples", "berry" matches "berries"
                elif item_words and self._is_plural_match(query_lower, item_words[0]):
                    base_score = 0.95  # Same as exact match
                    is_first_word_match = True
                # GOOD: Query is a complete word in the name
                elif query_lower in item_words:
                    base_score = 0.85
                # OK: Query is at start of first word (e.g., "chick" matches "chicken")
                elif item_words and item_words[0].startswith(query_lower) and len(query_lower) >= 4:
                    base_score = 0.75
                
                # Apply score adjustments
                if base_score > 0:
                    # Prefer shorter names (more specific)
                    # E.g., "Apples, raw" (2 words) > "Apple juice, unsweetened" (3 words)
                    word_count = len(item_words)
                    word_count_penalty = min(word_count * 0.01, 0.05)  # Max 5% penalty
                    
                    # Bonus for first word matches with fewer total words
                    if is_first_word_match and word_count <= 3:
                        word_count_penalty *= 0.5  # Reduce penalty for short, specific matches
                    
                    final_score = base_score - word_count_penalty
                    
                    word_matches.append((item, final_score))
            
            # Sort by score (descending)
            word_matches.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"USDA matches found: {len(word_matches)}")
            if word_matches:
                logger.info(f"Top USDA match: {word_matches[0][0]['original_name']} (score: {word_matches[0][1]})")
            
            # Add top USDA matches
            for item, score in word_matches[:10]:  # Get more candidates
                results.append((item["data"], item["source"], score))
            
            # If we found good USDA matches, return them immediately
            if results and results[0][2] >= 0.75:
                logger.info(f"Found USDA ingredient: {results[0][0].get('description')} (score: {results[0][2]})")
                # Sort by score and return top results
                results.sort(key=lambda x: x[2], reverse=True)
                return results[:top_k]
            
            # If no good word matches, try fuzzy matching on USDA
            if not word_matches:
                usda_fuzzy = process.extract(query_lower, self.usda_names, scorer=fuzz.WRatio, limit=5)
                for name, score, _ in usda_fuzzy:
                    if score >= 60:
                        for item in self.usda_index:
                            if item["name"] == name:
                                results.append((item["data"], item["source"], score / 100.0))
                                break
                
                if results:
                    results.sort(key=lambda x: x[2], reverse=True)
                    logger.info(f"Found USDA via fuzzy match: {results[0][0].get('description')}")
                    return results[:top_k]
        
        # Step 3: Search dishes (for multi-word queries or if USDA search failed)
        # Note: Reset results here because single-word queries only reach this point
        # if no good USDA matches (score >= 0.75) were found. We prefer trying dish
        # search over returning low-confidence USDA matches.
        results = []
        
        # Search dishes in selected country FIRST
        if self.dish_names:
            country_dishes = [(item["name"], item) for item in self.dish_index if item["country"] == country_lower]
            if country_dishes: 
                country_dish_names = [d[0] for d in country_dishes]
                matches = process.extract(query_lower, country_dish_names, scorer=fuzz.WRatio, limit=3)
                
                for name, score, _ in matches:
                    if score >= 70: 
                        for dish_name, item in country_dishes: 
                            if dish_name == name:
                                results.append((item["data"], item["source"], score / 100.0))
                                break
        
        # Step 4: If no good matches in selected country, search all dishes
        if not results or (results and results[0][2] < 0.8):
            matches = process.extract(query_lower, self.dish_names, scorer=fuzz.WRatio, limit=3)
            
            for name, score, _ in matches: 
                if score >= 70:
                    for item in self.dish_index:
                        if item["name"] == name: 
                            final_score = score / 100.0
                            if item["country"] != country_lower: 
                                final_score *= 0.9
                            results.append((item["data"], item["source"], final_score))
                            break
        
        # Step 5: Search USDA (for multi-word queries that didn't find dishes) - IMPROVED MATCHING
        if self.usda_names:
            # First:  Find items where query is a WORD in the name (not just substring)
            word_matches = []
            for item in self.usda_index: 
                item_words = self._normalize_item_name(item["name"])
                # Check if query matches the FIRST word (most relevant)
                if item_words and item_words[0] == query_lower: 
                    word_matches.append((item, 0.95))
                # Check if query is any word in the name
                elif query_lower in item_words:
                    word_matches.append((item, 0.85))
            
            # Sort by score and add to results
            word_matches.sort(key=lambda x: x[1], reverse=True)
            for item, score in word_matches[: 5]: 
                results.append((item["data"], item["source"], score))
            
            # If no word matches, try fuzzy matching
            if not word_matches:
                usda_matches = process.extract(query_lower, self.usda_names, scorer=fuzz.WRatio, limit=3)
                for name, score, _ in usda_matches:
                    if score >= 60:
                        for item in self.usda_index: 
                            if item["name"] == name: 
                                results.append((item["data"], item["source"], score / 100.0))
                                break
        
        # Sort by score
        results.sort(key=lambda x:  x[2], reverse=True)
        
        # Remove duplicates
        seen = set()
        unique = []
        for data, source, conf in results:
            name = data.get("dish_name") or data.get("description", "")
            if name.lower() not in seen:
                seen.add(name.lower())
                unique.append((data, source, conf))
        
        logger.info(f"Found {len(unique)} results")
        if unique:
            logger.info(f"Top result: {unique[0][0].get('dish_name') or unique[0][0].get('description')}")
        
        return unique[: top_k]
    
    def search_ingredient(self, query: str, top_k: int = 3) -> List[Tuple[Dict, str, float]]: 
        """Search USDA only"""
        query_lower = query.lower().strip()
        results = []
        
        # Contained matches
        for item in self.usda_index:
            if query_lower in item["name"]: 
                score = len(query_lower) / len(item["name"]) + 0.5
                results.append((item["data"], item["source"], min(score, 0.95)))
        
        if results:
            results.sort(key=lambda x: x[2], reverse=True)
            return results[:top_k]
        
        # Fuzzy match
        if self.usda_names:
            matches = process.extract(query_lower, self.usda_names, scorer=fuzz.WRatio, limit=top_k)
            for name, score, _ in matches:
                if score >= 50:
                    for item in self.usda_index: 
                        if item["name"] == name: 
                            results.append((item["data"], item["source"], score / 100.0))
                            break
        
        return results[: top_k]