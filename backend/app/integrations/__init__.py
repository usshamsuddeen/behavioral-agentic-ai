"""
Integrations Package
Third-party service integrations (WhatsApp, Telegram, etc.)
"""

from app.integrations.whatsapp import (
    WhatsAppClient,
    WhatsAppConfig,
    get_whatsapp_client,
    is_whatsapp_configured
)

__all__ = [
    "WhatsAppClient",
    "WhatsAppConfig",
    "get_whatsapp_client",
    "is_whatsapp_configured"
]
