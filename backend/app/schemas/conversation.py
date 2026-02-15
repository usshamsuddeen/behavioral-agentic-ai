"""
Conversation Schemas - Request/Response models for conversations
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation"""
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_email: str = Field(..., min_length=5, max_length=255)
    preferred_language: str = Field(default="en", max_length=10)
    language_name: str = Field(default="English", max_length=50)
    language_flag: str = Field(default="🇺🇸", max_length=10)
    initial_message: Optional[str] = None


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    status: Optional[str] = None
    priority: Optional[str] = None
    is_escalated: Optional[bool] = None
    escalation_reason: Optional[str] = None


class MessagePreview(BaseModel):
    """Simplified message for conversation list"""
    id: int
    content: str
    sender_type: str
    sentiment: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Full conversation response with messages"""
    id: int
    customer_id: int
    customer_name: str
    customer_email: str
    customer_avatar: str
    
    # Status
    status: str
    priority: str
    
    # Sentiment
    current_sentiment: str
    sentiment_score: float
    frustration_level: float
    sentiment_emoji: str
    
    # Escalation
    is_escalated: bool
    escalation_reason: Optional[str]
    
    # Language
    detected_language: str
    language_name: str
    language_flag: str
    
    # Summary
    last_message_preview: Optional[str]
    message_count: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    time_ago: str
    
    # Messages (optional)
    messages: Optional[List[MessagePreview]] = None

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response for list of conversations"""
    total: int
    conversations: List[ConversationResponse]
