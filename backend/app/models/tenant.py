"""
Tenant Model — Multi-Tenant Organization
FRD v3.0 Zone 7 (FR-7.3) — Tenant Isolation
Each CLIENT (store owner) gets one Tenant record on signup.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import secrets

from app.database import Base


class Tenant(Base):
    """
    Multi-tenant organization model.
    Created automatically when a CLIENT signs up.
    All data (conversations, KB, widget config) is scoped to a tenant.
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)

    # Business Info (FR-2.1)
    name = Column(String(200), nullable=False)  # Company/Store name
    industry = Column(String(100), nullable=True)  # Fashion, Electronics, etc.
    description = Column(Text, nullable=True)  # Used to personalize AI responses
    support_email = Column(String(255), nullable=True)  # Escalation notifications
    timezone = Column(String(50), default="UTC")

    # Store Connection (FR-2.2)
    store_url = Column(String(500), nullable=True)
    store_platform = Column(String(50), nullable=True)  # shopify, woocommerce, wix, squarespace, custom

    # Widget API Key (FR-6.1, FR-7.3.4)
    widget_api_key = Column(String(100), unique=True, index=True, nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)  # 0-5

    # Owner (FK to users table)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", foreign_keys=[owner_id])

    # Relationships
    widget_config = relationship("WidgetConfig", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="tenant", cascade="all, delete-orphan")
    escalations = relationship("Escalation", back_populates="tenant", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a unique widget API key: wk_ + 32 random chars"""
        return f"wk_{secrets.token_urlsafe(32)}"

    def to_dict(self) -> dict:
        """Convert tenant to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "description": self.description,
            "support_email": self.support_email,
            "timezone": self.timezone,
            "store_url": self.store_url,
            "store_platform": self.store_platform,
            "widget_api_key": self.widget_api_key,
            "is_active": self.is_active,
            "onboarding_completed": self.onboarding_completed,
            "onboarding_step": self.onboarding_step,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Tenant {self.name} (ID: {self.id})>"
