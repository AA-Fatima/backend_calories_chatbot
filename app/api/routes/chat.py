from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, Intent, CalorieResult
from app.core.nlp_engine import NLPEngine
from app.services.food_search import FoodSearchService
from app.services.calorie_calculator import CalorieCalculatorService
from app.services.conversation_manager import ConversationManager
from app.services.fallback_service import FallbackService
from app.services.missing_dish_logger import MissingDishLogger
from typing import Dict
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter()

# These will be initialized in main.py
app_state:  Dict = {}


def get_nlp_engine() -> NLPEngine:
    return app_state.get("nlp_engine")


def get_food_search() -> FoodSearchService:
    return app_state.get("food_search")


def get_calorie_calculator() -> CalorieCalculatorService:
    return app_state.get("calorie_calculator")


def get_conversation_manager() -> ConversationManager: 
    return app_state.get("conversation_manager")


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Process a chat message and return calorie information"""
    
    try:
        nlp_engine = get_nlp_engine()
        calorie_calculator = get_calorie_calculator()
        conversation_manager = get_conversation_manager()
        
        if not nlp_engine or not calorie_calculator: 
            logger.error("Services not initialized")
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Get or create session
        session = conversation_manager.get_session(request.session_id)
        if not session:
            request.session_id = conversation_manager.create_session(request.country)
            session = conversation_manager.get_session(request.session_id)
        
        # Get conversation context
        context = conversation_manager.get_context(request.session_id)
        
        # Parse the user's message
        logger.info(f"Parsing query: {request.message}")
        parsed_query = nlp_engine.parse_query(request.message, context)
        logger.info(f"Parsed query: intent={parsed_query.intent}, foods={parsed_query.food_items}")
        
        # Handle different intents
        if parsed_query.intent == Intent.GREETING:
            response_message = generate_greeting_response(request.country)
            return ChatResponse(
                message=response_message,
                calorie_result=None,
                session_id=request.session_id
            )
        
        if parsed_query.intent == Intent.HELP:
            response_message = generate_help_response()
            return ChatResponse(
                message=response_message,
                calorie_result=None,
                session_id=request.session_id
            )
        
        # Calculate calories
        logger.info(f"Calculating calories for: {parsed_query.food_items}")
        calorie_result = await calorie_calculator.calculate(parsed_query, request.country, context)
        logger.info(f"Result: {calorie_result.food_name} = {calorie_result.total_calories} kcal")
        
        # Generate response message
        if calorie_result.source == "not_found" or calorie_result.total_calories == 0:
            response_message = generate_not_found_response(
                parsed_query.food_items[0] if parsed_query.food_items else request.message
            )
            return ChatResponse(
                message=response_message,
                calorie_result=None,
                requires_clarification=True,
                session_id=request.session_id
            )
        
        response_message = generate_calorie_response(calorie_result)
        
        # Update session context
        conversation_manager.update_session(
            request.session_id,
            last_dish=calorie_result.food_name,
            last_result=calorie_result.model_dump(),
            awaiting_ingredients=False
        )
        
        return ChatResponse(
            message=response_message,
            calorie_result=calorie_result,
            session_id=request.session_id
        )
        
    except Exception as e: 
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session")
async def create_session(country: str = "lebanon"):
    """Create a new chat session"""
    conversation_manager = get_conversation_manager()
    if not conversation_manager: 
        raise HTTPException(status_code=500, detail="Conversation manager not initialized")
    session_id = conversation_manager.create_session(country)
    return {"session_id":  session_id, "country": country}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    conversation_manager = get_conversation_manager()
    if not conversation_manager:
        raise HTTPException(status_code=500, detail="Conversation manager not initialized")
    session = conversation_manager.get_session(session_id)
    if not session: 
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def generate_greeting_response(country: str) -> str:
    """Generate greeting response"""
    country_greetings = {
        "lebanon": "Marhaba! 🇱🇧",
        "syria": "Ahlan wa sahlan!  🇸🇾",
        "egypt": "Ahlan!  🇪🇬",
        "saudi":  "Marhaba! 🇸🇦",
        "iraq": "Ahlan bik! 🇮🇶",
    }
    greeting = country_greetings.get(country.lower(), "Hello!")
    
    return f"""{greeting} Welcome to the Arabic Food Calorie Calculator!

I can help you find calorie information for: 
- Single ingredients (e.g., "apple", "rice", "chicken")
- Traditional dishes (e.g., "shawarma", "kushari", "kabsa")

You can also: 
- Modify dishes:  "shawarma without fries"
- Add ingredients: "falafel with extra tahini"
- Specify quantities: "200g chicken breast"

What would you like to know about?"""


def generate_help_response() -> str:
    """Generate help response"""
    return """How to use the Calorie Calculator: 

1. Ask about any food: 
   - "How many calories in shawarma?"
   - "Calories in kushari"
   - "Apple calories"

2. Modify dishes:
   - "Fajita without fries"
   - "Kabsa without rice"

3. Add ingredients:
   - "Shawarma with extra garlic sauce"
   - "Falafel with pickles"

4. Specify quantities:
   - "200g grilled chicken"
   - "Double portion of rice"

Just type your question and I'll help you!"""


def generate_calorie_response(result: CalorieResult) -> str:
    """Generate response for calorie result"""
    
    food_name = result.food_name.title() if result.food_name else "Unknown"
    total_cal = int(result.total_calories) if result.total_calories else 0
    total_weight = int(result.weight_g) if result.weight_g else 0
    
    if result.is_approximate:
        accuracy_note = "\n(This is an approximate estimate)"
    else:
        accuracy_note = ""
    
    response = f"""{food_name}

Nutrition Information:
- Total Calories: {total_cal} kcal
- Total Weight: {total_weight}g
"""
    
    if result.ingredients and len(result.ingredients) > 0:
        response += "\nIngredients breakdown:\n"
        for ing in result.ingredients[: 10]: 
            ing_cal = int(ing.calories) if ing.calories else 0
            ing_weight = int(ing.weight_g) if ing.weight_g else 0
            response += f"  - {ing.name}: {ing_cal} kcal ({ing_weight}g)\n"
    
    if result.modifications: 
        response += "\nModifications:\n"
        for mod in result.modifications: 
            response += f"  - {mod}\n"
    
    response += accuracy_note
    response += "\n\nYou can modify this dish by saying 'without [ingredient]' or 'add [ingredient]'"
    
    return response


def generate_not_found_response(food_name: str) -> str:
    """Generate response when food is not found"""
    return f"""I couldn't find "{food_name}" in my database. 

This could be because: 
- It's spelled differently than I expect
- It's a regional dish I don't have yet

Can you help me?  Please tell me: 
1. What are the main ingredients in this dish?
2.  Approximately how much of each ingredient? 

For example:  "chicken 200g, rice 150g, onion 50g"

This will help me calculate the calories! """