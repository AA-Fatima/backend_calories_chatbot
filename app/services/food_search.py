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
    
    def search(self, query:  str, country: str = "", top_k: int = 5) -> List[Tuple[Dict, str, float]]:
        """Search for food"""
        query_lower = query.lower().strip()
        country_lower = country.lower().strip() if country else ""
        
        if not query_lower: 
            return []
        
        logger.info(f"Searching for:  '{query_lower}' (country: {country_lower})")
        
        # Step 1: Exact match
        for item in self.search_index:
            if query_lower == item["name"]:
                if item["source"] == "dishes":
                    if not country_lower or item["country"] == country_lower:
                        logger.info(f"Exact match:  {item['original_name']}")
                        return [(item["data"], item["source"], 1.0)]
                else:
                    logger.info(f"Exact USDA match: {item['original_name']}")
                    return [(item["data"], item["source"], 1.0)]
        
        results = []
        
        # Step 2: Search dishes in selected country FIRST
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
        
        # Step 3: If no good matches in selected country, search all dishes
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
        
        # Step 4: Search USDA - IMPROVED MATCHING
        if self.usda_names:
            # Normalize the query for better matching
            normalized_query = self._normalize_ingredient_name(query_lower)
            
            # First: Find items where query is a WORD in the name (not just substring)
            word_matches = []
            for item in self.usda_index:
                normalized_item_name = self._normalize_ingredient_name(item["name"])
                item_words = normalized_item_name.split()
                query_words = normalized_query.split()
                
                # Check for exact word matches
                if normalized_query == normalized_item_name:
                    # Perfect match
                    word_matches.append((item, 1.0))
                elif len(query_words) == 1:
                    # Single word query - check if it's the first or any significant word
                    query_word = query_words[0]
                    if item_words and item_words[0] == query_word:
                        # Query matches first word (most relevant)
                        word_matches.append((item, 0.95))
                    elif query_word in item_words:
                        # Query is any word in the name
                        word_matches.append((item, 0.85))
                else:
                    # Multi-word query - check if all words are in the item
                    if all(qw in item_words for qw in query_words):
                        word_matches.append((item, 0.90))
            
            # Sort by score and add to results
            word_matches.sort(key=lambda x: x[1], reverse=True)
            for item, score in word_matches[:5]: 
                results.append((item["data"], item["source"], score))
            
            # If no word matches, try fuzzy matching
            if not word_matches:
                usda_matches = process.extract(query_lower, self.usda_names, scorer=fuzz.WRatio, limit=5)
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
            logger.info(f"Top result: {unique[0][0].get('dish_name') or unique[0][0].get('description')} (score: {unique[0][2]:.2f})")
        
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
    
    def _normalize_ingredient_name(self, name: str) -> str:
        """Normalize ingredient name for better matching"""
        # Convert to lowercase
        name = name.lower().strip()
        
        # Replace punctuation with spaces
        name = name.replace(',', ' ').replace('-', ' ').replace('/', ' ')
        
        # Remove only minimally impactful words
        # Note: We keep 'cooked', 'dried' etc as they affect caloric content
        remove_words = ['organic', 'fresh']
        words = name.split()
        words = [w for w in words if w not in remove_words]
        
        # Join and clean up spaces
        name = ' '.join(words).strip()
        
        return name