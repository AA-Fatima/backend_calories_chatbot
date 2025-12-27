import httpx
from typing import Dict, Any, Optional
from app.config import settings
import logging
import re

logger = logging.getLogger(__name__)

class FallbackService:
    """Fallback to GPT/DeepSeek when dish not found"""
    
    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY
        self.deepseek_key = settings.DEEPSEEK_API_KEY
    
    async def get_calories_from_gpt(self, food_name: str, country: str) -> Optional[Dict[str, Any]]:
        """Get calorie estimate from ChatGPT"""
        if not self.openai_key:
            logger.warning("OpenAI API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_key}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role":  "system", "content": "You are a nutrition expert. Provide calorie estimates for foods. Always respond with a JSON object containing:  calories (number), weight_g (number), confidence (low/medium/high), ingredients (array of objects with name, weight_g, calories)."},
                            {"role": "user", "content": f"Estimate the calories in {food_name} as prepared in {country}. Provide typical serving size."}
                        ],
                        "temperature": 0.3
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    return self._parse_response(content, food_name)
        except Exception as e: 
            logger.error(f"GPT API error: {e}")
        
        return None
    
    async def get_calories_from_deepseek(self, food_name:  str, country: str) -> Optional[Dict[str, Any]]:
        """Get calorie estimate from DeepSeek"""
        if not self.deepseek_key:
            logger.warning("DeepSeek API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {self.deepseek_key}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content":  "You are a nutrition expert. Provide calorie estimates for foods. Respond with JSON:  {calories, weight_g, ingredients:  [{name, weight_g, calories}]}"},
                            {"role": "user", "content": f"Calories in {food_name} ({country} style)?"}
                        ]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    return self._parse_response(content, food_name)
        except Exception as e: 
            logger.error(f"DeepSeek API error:  {e}")
        
        return None
    
    def _parse_response(self, content: str, food_name: str) -> Dict[str, Any]:
        """Parse LLM response"""
        import json
        
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "food_name": food_name,
                    "calories": float(data.get("calories", 0)),
                    "weight_g": float(data.get("weight_g", 100)),
                    "ingredients": data.get("ingredients", []),
                    "is_approximate": True
                }
        except: 
            pass
        
        # Try to extract calories from text
        cal_match = re.search(r'(\d+(? :\.\d+)?)\s*(? :calories|kcal|cal)', content, re.IGNORECASE)
        if cal_match:
            return {
                "food_name": food_name,
                "calories": float(cal_match.group(1)),
                "weight_g": 100,
                "ingredients":  [],
                "is_approximate": True
            }
        
        return None