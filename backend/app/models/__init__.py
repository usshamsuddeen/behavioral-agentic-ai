"""Models package - Database models for the application — FRD v4.0"""

from app.models.user import User, UserSession, UserSettings
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.knowledge_document import KnowledgeDocument
from app.models.escalation import Escalation
from app.models.audit_log import AuditLog
from app.models.order import CustomerOrder  # ★ V4 NEW — Zone 8
from app.models.product_listing import ProductListing  # ★ V4 NEW — Zone 3

__all__ = [
    "User", "UserSession", "UserSettings",
    "Tenant", "WidgetConfig",
    "Conversation", "Message",
    "KnowledgeDocument", "Escalation", "AuditLog",
    "CustomerOrder",  # ★ V4
    "ProductListing",  # ★ V4
]

