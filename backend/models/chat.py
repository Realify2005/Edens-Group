from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# models/chat_models.py
class UserQueryParsed(BaseModel):
    mental_health_intent: Optional[str] = None
    location_suburb: Optional[str] = None
    target_population: List[str] = []
    cost_preference: Optional[str] = None
    urgency_level: str = "routine"
    semantic_query: str

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    services: List[dict] = []
    conversation_id: str