"""
Message Schemas - Request/Response models for messages
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    conversation_id: int
    content: str = Field(..., min_length=1, max_length=5000)
    sender_type: str = Field(default="customer")  # customer, agent, ai
    sender_name: Optional[str] = None


class MessageResponse(BaseModel):
    """Full message response with sentiment"""
    id: int
    conversation_id: int
    content: str
    sender_type: str
    sender_name: Optional[str]
    
    # Sentiment
    sentiment: str
    sentiment_score: float
    sentiment_label: Optional[str]
    sentiment_emoji: str
    
    # Language
    detected_language: Optional[str]
    
    # Flags
    is_escalation_trigger: bool
    
    # Timestamps
    created_at: datetime
    time_ago: str

    class Config:
        from_attributes = True


class SentimentAnalysisRequest(BaseModel):
    """Request for sentiment analysis"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = None


class SentimentAnalysisResponse(BaseModel):
    """Response from sentiment analysis"""
    text: str
    sentiment: str  # positive, neutral, negative
    score: float  # 0.0 to 1.0
    label: str  # Human readable label
    emoji: str
    confidence: float
    detected_language: str


class LanguageDetectionRequest(BaseModel):
    """Request for language detection"""
    text: str = Field(..., min_length=1, max_length=5000)


class LanguageDetectionResponse(BaseModel):
    """Response from language detection"""
    text: str
    language_code: str
    language_name: str
    language_flag: str
    confidence: float
