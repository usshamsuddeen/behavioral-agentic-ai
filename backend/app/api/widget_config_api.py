"""
Widget Configuration API — Zone 3: Widget Management
FRD v3.0 (FR-3.5)

CRUD endpoints for widget appearance, behavior, and embed code.
All endpoints require JWT authentication and are tenant-scoped.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.middleware.jwt import get_current_user, get_tenant_for_user, require_role

router = APIRouter(prefix="/api/widget", tags=["Widget Config"])

# Backend URL for embed script
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class UpdateWidgetConfigRequest(BaseModel):
    """FR-3.5.1: Widget appearance and behavior settings"""
    theme_color: Optional[str] = None
    position: Optional[str] = None      # bottom-right, bottom-left
    bot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    placeholder_text: Optional[str] = None
    is_active: Optional[bool] = None
    show_branding: Optional[bool] = None
    pre_chat_form_enabled: Optional[bool] = None
    pre_chat_fields: Optional[str] = None  # JSON string


# ═══════════════════════════════════════════════════════════════════
# FR-3.5.1: Get Widget Configuration
# ═══════════════════════════════════════════════════════════════════

@router.get("/config")
async def get_widget_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    FR-3.5.1: Get current widget configuration for this tenant.
    Returns appearance settings, behavior toggles, and embed status.
    """
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()
    
    if not config:
        # Auto-create default config if missing
        config = WidgetConfig(
            tenant_id=tenant.id,
            theme_color="#6366f1",
            position="bottom-right",
            bot_name="AI Assistant",
            welcome_message="Hello! How can I help you today?",
            placeholder_text="Type your message...",
            is_active=False,
            show_branding=True,
            pre_chat_form_enabled=False
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return {
        "id": config.id,
        "tenant_id": config.tenant_id,
        "theme_color": config.theme_color,
        "position": config.position,
        "bot_name": config.bot_name,
        "welcome_message": config.welcome_message,
        "placeholder_text": config.placeholder_text,
        "is_active": config.is_active,
        "show_branding": config.show_branding,
        "pre_chat_form_enabled": config.pre_chat_form_enabled,
        "pre_chat_fields": config.get_pre_chat_fields() if hasattr(config, 'get_pre_chat_fields') else [],
        "api_key": tenant.widget_api_key,
        "embed_code": _generate_embed_code(tenant.widget_api_key),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.5.1–FR-3.5.5: Update Widget Configuration
# ═══════════════════════════════════════════════════════════════════

@router.put("/config")
async def update_widget_config(
    data: UpdateWidgetConfigRequest,
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """
    FR-3.5.1–FR-3.5.5: Update widget appearance and behavior.
    Supports: color, position, bot name, messages, pre-chat form, enable/disable.
    """
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Widget not configured. Complete onboarding first.")
    
    # Apply updates
    if data.theme_color is not None:
        config.theme_color = data.theme_color
    if data.position is not None:
        config.position = data.position
    if data.bot_name is not None:
        config.bot_name = data.bot_name
    if data.welcome_message is not None:
        config.welcome_message = data.welcome_message
    if data.placeholder_text is not None:
        config.placeholder_text = data.placeholder_text
    if data.is_active is not None:
        config.is_active = data.is_active
    if data.show_branding is not None:
        config.show_branding = data.show_branding
    if data.pre_chat_form_enabled is not None:
        config.pre_chat_form_enabled = data.pre_chat_form_enabled
    if data.pre_chat_fields is not None:
        config.pre_chat_fields = data.pre_chat_fields
    
    config.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Widget configuration updated successfully",
        "config": {
            "theme_color": config.theme_color,
            "position": config.position,
            "bot_name": config.bot_name,
            "welcome_message": config.welcome_message,
            "is_active": config.is_active
        }
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.5.4: Get Embed Code
# ═══════════════════════════════════════════════════════════════════

@router.get("/embed-code")
async def get_embed_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.5.4: Get the HTML embed code snippet for this tenant's widget"""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    embed_code = _generate_embed_code(tenant.widget_api_key)
    
    return {
        "api_key": tenant.widget_api_key,
        "embed_code": embed_code,
        "instructions": (
            "Add this code snippet just before the closing </body> tag "
            "on every page where you want the chat widget to appear."
        )
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.5.5: Toggle Widget Active/Inactive
# ═══════════════════════════════════════════════════════════════════

@router.post("/toggle")
async def toggle_widget(
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """FR-3.5.5: Toggle widget active/inactive state"""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Widget not configured")
    
    config.is_active = not config.is_active
    config.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "is_active": config.is_active,
        "message": f"Widget {'activated' if config.is_active else 'deactivated'} successfully"
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.5.6: Widget Analytics Summary
# ═══════════════════════════════════════════════════════════════════

@router.get("/analytics")
async def get_widget_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    FR-3.5.6: Get widget analytics summary
    Returns total loads, conversations started, and avg session duration (last 7 days)
    """
    from app.models.conversation import Conversation
    from datetime import timedelta
    
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    # Calculate 7 days ago
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # Count conversations with session_id (widget-initiated conversations)
    widget_conversations = db.query(Conversation).filter(
        Conversation.tenant_id == tenant.id,
        Conversation.session_id.isnot(None),
        Conversation.created_at >= seven_days_ago
    ).all()
    
    total_loads = len(widget_conversations)
    conversations_started = total_loads
    
    # Calculate average session duration (time from created_at to updated_at)
    durations = []
    for conv in widget_conversations:
        if conv.updated_at and conv.created_at:
            duration = (conv.updated_at - conv.created_at).total_seconds()
            # Only include sessions longer than 0 seconds
            if duration > 0:
                durations.append(duration)
    
    avg_session_duration = sum(durations) / len(durations) if durations else 0
    
    return {
        "total_loads": total_loads,
        "conversations_started": conversations_started,
        "avg_session_duration": round(avg_session_duration, 2),
        "period": "Last 7 days"
    }


# ═══════════════════════════════════════════════════════════════════
# HELPER: Generate embed code snippet
# ═══════════════════════════════════════════════════════════════════

def _generate_embed_code(api_key: str) -> str:
    """Generate the HTML embed code for the widget — FR-6.1.1"""
    return (
        f'<!-- Behavioral AI Chat Widget -->\n'
        f'<script\n'
        f'  src="{BACKEND_URL}/widget/embed.js"\n'
        f'  data-widget-key="{api_key}"\n'
        f'  async>\n'
        f'</script>'
    )
