from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Country(str, Enum):
    LEBANON = "lebanon"
    SYRIA = "syria"
    IRAQ = "iraq"
    SAUDI = "saudi"
    EGYPT = "egypt"
    JORDAN = "jordan"
    PALESTINE = "palestine"
    MOROCCO = "morocco"
    TUNISIA = "tunisia"
    ALGERIA = "algeria"

class Ingredient(BaseModel):
    usda_fdc_id: Optional[int] = None
    name: str
    weight_g: float
    calories:  float

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: MessageRole
    content:  str
    timestamp:  datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    message:  str
    session_id: str
    country: str

class CalorieResult(BaseModel):
    food_name: str
    original_query: str
    total_calories: float
    weight_g: float
    ingredients: Optional[List[Ingredient]] = None
    modifications: Optional[List[str]] = None
    source: str  # "dishes", "usda", "gpt_fallback", "deepseek_fallback"
    confidence: float
    is_approximate: bool = False
    country: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    calorie_result: Optional[CalorieResult] = None
    follow_up_questions:  Optional[List[str]] = None
    requires_clarification: bool = False
    session_id: str

class Intent(str, Enum):
    QUERY_FOOD = "query_food"
    MODIFY_REMOVE = "modify_remove"
    MODIFY_ADD = "modify_add"
    MODIFY_QUANTITY = "modify_quantity"
    PROVIDE_INGREDIENTS = "provide_ingredients"
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"

class ParsedQuery(BaseModel):
    intent: Intent
    food_items: List[str]
    modifications: Dict[str, List[str]] = {"remove": [], "add":  []}
    quantities: Dict[str, float] = {}
    language_detected: str
    original_text: str
    normalized_text: str

class CountryInfo(BaseModel):
    code: str
    name_en: str
    name_ar: str
    flag_emoji: str
    dish_count: int = 0

class MissingDishLog(BaseModel):
    query: str
    country: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    fallback_response: Optional[Dict[str, Any]] = None
    resolved:  bool = False

class EvaluationResult(BaseModel):
    query: str
    expected_calories: float
    our_calories: Optional[float] = None
    gpt_calories: Optional[float] = None
    deepseek_calories:  Optional[float] = None
    our_error_percent: Optional[float] = None
    gpt_error_percent: Optional[float] = None
    deepseek_error_percent: Optional[float] = None