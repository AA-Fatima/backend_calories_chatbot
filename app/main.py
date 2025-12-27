from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api.routes import chat, countries, evaluation
from app. data.loaders import USDALoader, DishesLoader
from app. core.nlp_engine import NLPEngine
from app.services.food_search import FoodSearchService
from app.services. calorie_calculator import CalorieCalculatorService
from app. services.conversation_manager import ConversationManager
from app.services.fallback_service import FallbackService
from app.services. missing_dish_logger import MissingDishLogger
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging. INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    logger.info("🚀 Starting Arabic Calorie Chatbot...")
    
    # Load data
    logger.info("📂 Loading USDA Foundation data...")
    usda_foundation = USDALoader. load_foundation(settings.USDA_FOUNDATION_PATH)
    
    logger.info("📂 Loading USDA SR Legacy data...")
    usda_sr_legacy = USDALoader. load_sr_legacy(settings.USDA_SR_LEGACY_PATH)
    
    logger. info("📂 Loading dishes data...")
    dishes = DishesLoader. load(settings.DISHES_PATH)
    
    # Initialize NLP Engine
    logger.info("🧠 Initializing NLP Engine...")
    nlp_engine = NLPEngine()
    await nlp_engine. initialize()
    
    # Initialize services
    logger.info("⚙️ Initializing services...")
    food_search = FoodSearchService(usda_foundation, usda_sr_legacy, dishes, nlp_engine)
    fallback_service = FallbackService()
    missing_logger = MissingDishLogger()
    calorie_calculator = CalorieCalculatorService(food_search, fallback_service, missing_logger)
    conversation_manager = ConversationManager()
    
    # Store in app state (accessible from routes)
    chat. app_state["nlp_engine"] = nlp_engine
    chat.app_state["food_search"] = food_search
    chat.app_state["calorie_calculator"] = calorie_calculator
    chat.app_state["conversation_manager"] = conversation_manager
    chat.app_state["missing_logger"] = missing_logger
    
    logger.info("✅ All services initialized successfully!")
    logger.info(f"📊 Loaded:  {len(usda_foundation. get('all_foods', []))} USDA Foundation foods")
    logger.info(f"📊 Loaded:  {len(usda_sr_legacy. get('all_foods', []))} USDA SR Legacy foods")
    logger.info(f"📊 Loaded:  {len(dishes. get('all_dishes', []))} Arabic dishes")
    
    yield
    
    logger.info("👋 Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Arabic Food Calorie Chatbot API",
    description="A conversational AI for calculating calories in Arabic cuisine",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat. router, prefix="/api/chat", tags=["Chat"])
app.include_router(countries. router, prefix="/api/countries", tags=["Countries"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["Evaluation"])

@app.get("/")
async def root():
    return {
        "message":  "Arabic Food Calorie Chatbot API",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return {
        "status":  "healthy",
        "services": {
            "nlp_engine":  chat.app_state. get("nlp_engine") is not None,
            "food_search": chat.app_state.get("food_search") is not None,
            "calorie_calculator":  chat.app_state.get("calorie_calculator") is not None,
        }
    }