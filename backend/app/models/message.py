"""
Message Model - Individual messages in conversations
FRD v3.0 — Tenant-scoped messages with sentiment tracking
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class MessageSender(str, enum.Enum):
    """Who sent the message"""
    CUSTOMER = "customer"
    AGENT = "agent"
    AI = "ai"
    SYSTEM = "system"


class Message(Base):
    """
    Message model for individual chat messages.
    Stores content, sentiment analysis, and metadata.
    Scoped to a tenant (FR-7.3).
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant Isolation (FR-7.3)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # Conversation Reference
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    conversation = relationship("Conversation", back_populates="messages")

    # Content
    content = Column(Text, nullable=False)
    sender_type = Column(String(20), default=MessageSender.CUSTOMER.value)
    sender_name = Column(String(100), nullable=True)

    # Sentiment Analysis
    sentiment = Column(String(20), default="neutral")  # positive, neutral, negative
    sentiment_score = Column(Float, default=0.5)  # 0.0 to 1.0
    sentiment_label = Column(String(50), nullable=True)  # "Frustrated", "Happy", etc.

    # Language
    detected_language = Column(String(10), nullable=True)

    # Flags
    is_escalation_trigger = Column(Boolean, default=False)
    trigger_keywords = Column(Text, nullable=True)  # JSON array of detected keywords

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Message {self.id} - {self.sender_type}>"
