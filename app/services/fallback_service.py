"""
Fallback Service for Unknown Dishes
Uses GPT-4 and DeepSeek as fallback, logs missing dishes
"""

import logging
import json
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
import asyncio
import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class FallbackService:
    """
    Fallback service for dishes not in the database
    
    Features:
    1. GPT-4 API for calorie estimation
    2. DeepSeek API as alternative
    3. Structured prompts for consistent output
    4. Confidence scoring for estimates
    5. Missing dish logging for future database updates
    """
    
    SYSTEM_PROMPT = """You are a nutrition expert specializing in Arabic and Middle Eastern cuisine. 
When asked about calories in a dish, provide: 
1. Estimated total calories
2. Estimated weight in grams
3. Breakdown of main ingredients with their weights and calories
4. Confidence level (high/medium/low)

IMPORTANT: 
- Be specific to the country mentioned (e.g., Egyptian molokhia differs from Lebanese)
- Consider typical serving sizes in that region
- If unsure, indicate this is an estimate

Respond in this exact JSON format:
{
    "food_name": "Dish Name",
    "total_calories": 500,
    "weight_g": 300,
    "ingredients": [
        {"name": "Ingredient 1", "weight_g": 100, "calories": 150},
        {"name": "Ingredient 2", "weight_g": 50, "calories": 80}
    ],
    "confidence": "medium",
    "notes": "Any relevant notes about regional variations"
}"""

    def __init__(self):
        self.openai_client = None
        self.deepseek_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize API clients"""
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ OpenAI client initialized")
        
        if settings.DEEPSEEK_API_KEY:
            self.deepseek_client = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            logger.info("✅ DeepSeek client initialized")
    
    async def get_fallback_calories(
        self,
        food_name: str,
        country: str,
        modifications: Optional[Dict] = None,
        provider: str = "openai"  # or "deepseek"
    ) -> Tuple[Optional[Dict], str]:
        """
        Get calorie estimate from LLM fallback
        
        Returns:
            Tuple of (result_dict, provider_used)
        """
        
        # Build the query
        query = f"What are the calories in {food_name}"
        if country:
            query += f" as prepared in {country}"
        if modifications: 
            if modifications.get('remove'):
                query += f" without {', '.join(modifications['remove'])}"
            if modifications.get('add'):
                query += f" with added {', '.join(modifications['add'])}"
        
        # Try primary provider
        try:
            if provider == "openai" and self.openai_client:
                result = await self._query_openai(query)
                if result:
                    return result, "openai"
            elif provider == "deepseek" and self.deepseek_client:
                result = await self._query_deepseek(query)
                if result:
                    return result, "deepseek"
        except Exception as e: 
            logger.warning(f"Primary provider {provider} failed: {e}")
        
        # Try fallback provider
        try: 
            if provider == "openai" and self.deepseek_client: 
                result = await self._query_deepseek(query)
                if result: 
                    return result, "deepseek"
            elif provider == "deepseek" and self.openai_client:
                result = await self._query_openai(query)
                if result: 
                    return result, "openai"
        except Exception as e:
            logger.warning(f"Fallback provider failed: {e}")
        
        return None, "none"
    
    async def _query_openai(self, query: str) -> Optional[Dict]: 
        """Query OpenAI GPT-4"""
        try: 
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            # Parse JSON from response
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI query failed: {e}")
            return None
    
    async def _query_deepseek(self, query:  str) -> Optional[Dict]:
        """Query DeepSeek"""
        try: 
            response = await self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            return self._parse_llm_response(content)
            
        except Exception as e: 
            logger.error(f"DeepSeek query failed:  {e}")
            return None
    
    def _parse_llm_response(self, content: str) -> Optional[Dict]:
        """Parse LLM response to extract JSON"""
        try: 
            # Try to find JSON in the response
            json_match = content
            
            # If response contains markdown code blocks
            if '```json' in content: 
                start = content.find('```json') + 7
                end = content.find('```', start)
                json_match = content[start: end].strip()
            elif '```' in content:
                start = content.find('```') + 3
                end = content.find('```', start)
                json_match = content[start:end].strip()
            
            result = json.loads(json_match)
            
            # Validate required fields
            if 'total_calories' in result and 'food_name' in result:
                result['is_approximate'] = True
                result['source'] = 'llm_fallback'
                return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
        
        return None
    
    async def compare_providers(
        self,
        food_name: str,
        country: str
    ) -> Dict[str, Any]:
        """
        Get estimates from both providers for comparison
        Used for evaluation and thesis analysis
        """
        results = {}
        
        # Query both in parallel
        openai_task = self.get_fallback_calories(food_name, country, provider="openai")
        deepseek_task = self.get_fallback_calories(food_name, country, provider="deepseek")
        
        openai_result, deepseek_result = await asyncio.gather(
            openai_task, 
            deepseek_task,
            return_exceptions=True
        )
        
        if not isinstance(openai_result, Exception):
            results['openai'] = openai_result[0]
        
        if not isinstance(deepseek_result, Exception):
            results['deepseek'] = deepseek_result[0]
        
        return results


class MissingDishLogger:
    """
    Logs dishes not found in database for future additions
    """
    
    def __init__(self, log_file: str = "missing_dishes.json"):
        self.log_file = log_file
        self.missing_dishes:  Dict[str, Dict] = self._load_existing()
    
    def _load_existing(self) -> Dict:
        """Load existing missing dishes log"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def log(
        self,
        query: str,
        country: str,
        fallback_result: Optional[Dict],
        user_provided_ingredients: Optional[Dict] = None
    ):
        """Log a missing dish"""
        
        key = f"{query.lower()}_{country.lower()}"
        
        if key not in self.missing_dishes:
            self.missing_dishes[key] = {
                'query':  query,
                'country': country,
                'first_seen': datetime.utcnow().isoformat(),
                'count': 0,
                'fallback_results': [],
                'user_provided': []
            }
        
        entry = self.missing_dishes[key]
        entry['count'] += 1
        entry['last_seen'] = datetime.utcnow().isoformat()
        
        if fallback_result: 
            entry['fallback_results'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'result': fallback_result
            })
        
        if user_provided_ingredients: 
            entry['user_provided'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'ingredients': user_provided_ingredients
            })
        
        self._save()
    
    def _save(self):
        """Save to file"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.missing_dishes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save missing dishes:  {e}")
    
    def get_most_requested(self, limit:  int = 20) -> list:
        """Get most frequently requested missing dishes"""
        sorted_dishes = sorted(
            self.missing_dishes.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        return sorted_dishes[:limit]
    
    def export_for_dataset_update(self) -> list:
        """Export missing dishes in format ready for dataset update"""
        export_data = []
        for key, data in self.missing_dishes.items():
            if data['count'] >= 3:  # Only export if requested 3+ times
                export_entry = {
                    'dish_name': data['query'],
                    'country': data['country'],
                    'request_count': data['count'],
                    'suggested_calories': None,
                    'suggested_ingredients': None
                }
                
                # Get average from fallback results
                if data['fallback_results']:
                    calories = [
                        r['result'].get('total_calories', 0) 
                        for r in data['fallback_results'] 
                        if r['result']
                    ]
                    if calories: 
                        export_entry['suggested_calories'] = sum(calories) / len(calories)
                
                export_data.append(export_entry)
        
        return export_data