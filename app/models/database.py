from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.DATABASE_NAME]
            
            # Create indexes
            await cls.db.conversations.create_index("session_id")
            await cls.db.missing_dishes.create_index("timestamp")
            await cls.db.missing_dishes.create_index("resolved")
            
            logger.info("Connected to MongoDB")
        except Exception as e: 
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB"""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")
    
    @classmethod
    async def save_conversation(cls, session_id: str, messages: list):
        """Save conversation history"""
        await cls.db.conversations.update_one(
            {"session_id":  session_id},
            {"$set": {"messages": messages, "updated_at": datetime.utcnow()}},
            upsert=True
        )
    
    @classmethod
    async def get_conversation(cls, session_id: str) -> list:
        """Get conversation history"""
        doc = await cls.db.conversations.find_one({"session_id": session_id})
        return doc.get("messages", []) if doc else []
    
    @classmethod
    async def log_missing_dish(cls, log_data: dict):
        """Log a missing dish for later review"""
        await cls.db.missing_dishes.insert_one(log_data)
    
    @classmethod
    async def get_missing_dishes(cls, resolved: bool = False) -> list:
        """Get all missing dishes"""
        cursor = cls.db.missing_dishes.find({"resolved": resolved})
        return await cursor.to_list(length=1000)

from datetime import datetime