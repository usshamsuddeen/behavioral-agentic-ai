"""
Widget Configuration Model — Embeddable Chat Widget Settings
FRD v4.0 Zone 6 (FR-6.1) + Zone 3 (FR-3.5)
Stores appearance, behavior, and pre-chat form settings per tenant.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from app.database import Base


class WidgetConfig(Base):
    """
    Widget configuration for embeddable JS chat widget.
    One WidgetConfig per Tenant.
    Configured during onboarding (FR-2.3) and editable from dashboard (FR-3.5).
    """
    __tablename__ = "widget_configs"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant Reference (FR-7.3)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    tenant = relationship("Tenant", back_populates="widget_config")

    # Appearance (FR-2.3.1 — FR-2.3.4)
    position = Column(String(20), default="bottom-right")  # bottom-right | bottom-left
    theme_color = Column(String(10), default="#6366f1")  # Hex color for widget bubble/header
    welcome_message = Column(String(500), default="Hi! How can I help you today?")
    bot_name = Column(String(100), default="AI Assistant")

    # Pre-Chat Form (FR-2.3.5)
    pre_chat_form_enabled = Column(Boolean, default=False)
    pre_chat_fields = Column(Text, default='["name", "email"]')  # JSON array of field names

    # Input placeholder
    placeholder_text = Column(String(200), default="Type your message...")

    # Branding
    branding_logo_url = Column(String(500), nullable=True)
    show_branding = Column(Boolean, default=True)

    # Status
    is_active = Column(Boolean, default=True)

    # ★ V4: Widget Type (full | info | order | verify)
    widget_type = Column(String(20), default="full")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_pre_chat_fields(self) -> list:
        """Parse pre_chat_fields JSON string to list"""
        try:
            return json.loads(self.pre_chat_fields) if self.pre_chat_fields else []
        except (json.JSONDecodeError, TypeError):
            return ["name", "email"]

    def set_pre_chat_fields(self, fields: list):
        """Set pre_chat_fields from list"""
        self.pre_chat_fields = json.dumps(fields)

    def to_dict(self) -> dict:
        """Convert config to dictionary (safe for widget API response)"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "position": self.position,
            "theme_color": self.theme_color,
            "welcome_message": self.welcome_message,
            "bot_name": self.bot_name,
            "pre_chat_form_enabled": self.pre_chat_form_enabled,
            "pre_chat_fields": self.get_pre_chat_fields(),
            "placeholder_text": self.placeholder_text,
            "branding_logo_url": self.branding_logo_url,
            "show_branding": self.show_branding,
            "is_active": self.is_active,
            "widget_type": self.widget_type or "full",  # ★ V4
        }

    def to_public_dict(self) -> dict:
        """Widget-facing config (no internal IDs exposed)"""
        return {
            "position": self.position,
            "theme_color": self.theme_color,
            "welcome_message": self.welcome_message,
            "bot_name": self.bot_name,
            "pre_chat_form_enabled": self.pre_chat_form_enabled,
            "pre_chat_fields": self.get_pre_chat_fields(),
            "placeholder_text": self.placeholder_text,
            "branding_logo_url": self.branding_logo_url,
            "show_branding": self.show_branding,
            "widget_type": self.widget_type or "full",  # ★ V4
        }

    def __repr__(self):
        return f"<WidgetConfig tenant_id={self.tenant_id} color={self.theme_color}>"
