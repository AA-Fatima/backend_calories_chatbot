from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME:  str = "calorie_chatbot"
    
    # Data paths
    USDA_FOUNDATION_PATH: str = "app/data/raw/USDA_foundation.json"
    USDA_SR_LEGACY_PATH: str = "app/data/raw/USDA_sr_legacy.json"
    DISHES_PATH: str = "app/data/raw/dishes.xlsx"
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    
    # NLP Settings
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Supported countries
    SUPPORTED_COUNTRIES: List[str] = [
        "lebanon", "syria", "iraq", "saudi", "egypt",
        "jordan", "palestine", "morocco", "tunisia", "algeria"
    ]
    
    class Config: 
        env_file = ".env"
        extra = "allow"

settings = Settings()