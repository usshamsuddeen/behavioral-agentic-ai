"""
Escalation Model — Escalation Events & Handoff Tracking
FRD v3.0 §12: escalations table
Fields: id, conversation_id, tenant_id, priority, trigger_reasons, handoff_package, resolved_by

Provides a dedicated table for the escalation queue (FR-3.3).
Each row = one escalation event, linked to a conversation.
Contains the full handoff package (FR-5.3.10) for human agents.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from app.database import Base


class Escalation(Base):
    """
    Escalation event record.
    Created when a conversation triggers escalation (FR-5.3).
    Contains handoff package for human agent takeover.
    """
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True)

    # Conversation Reference
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation = relationship("Conversation", back_populates="escalations")

    # Tenant Isolation (FR-7.3)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant = relationship("Tenant", back_populates="escalations")

    # Escalation Details (FRD §12)
    priority = Column(String(20), default="high")  # low, normal, high, urgent
    trigger_reasons = Column(Text, nullable=True)  # JSON array of reasons
    trigger_score = Column(Float, default=0.0)  # 0.0 to 1.0

    # Sentiment Context at Escalation
    sentiment_at_escalation = Column(String(20), nullable=True)  # positive/neutral/negative
    sentiment_score_at_escalation = Column(Float, nullable=True)  # 0.0 to 1.0
    frustration_at_escalation = Column(Float, nullable=True)  # 0.0 to 1.0

    # Handoff Package (FR-5.3.10) — JSON blob
    handoff_package = Column(Text, nullable=True)  # Full context for human agent

    # Resolution
    status = Column(String(20), default="open")  # open, assigned, resolved, closed
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_trigger_reasons(self) -> list:
        """Parse trigger_reasons JSON to list"""
        try:
            return json.loads(self.trigger_reasons) if self.trigger_reasons else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_trigger_reasons(self, reasons: list):
        """Set trigger_reasons from list"""
        self.trigger_reasons = json.dumps(reasons)

    def get_handoff_package(self) -> dict:
        """Parse handoff_package JSON to dict"""
        try:
            return json.loads(self.handoff_package) if self.handoff_package else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_handoff_package(self, package: dict):
        """Set handoff_package from dict"""
        self.handoff_package = json.dumps(package)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "tenant_id": self.tenant_id,
            "priority": self.priority,
            "trigger_reasons": self.get_trigger_reasons(),
            "trigger_score": self.trigger_score,
            "sentiment_at_escalation": self.sentiment_at_escalation,
            "frustration_at_escalation": self.frustration_at_escalation,
            "status": self.status,
            "assigned_agent_id": self.assigned_agent_id,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Escalation {self.id} conv={self.conversation_id} priority={self.priority}>"
