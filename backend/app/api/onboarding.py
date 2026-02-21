"""
Onboarding API — Zone 2: 5-Step Onboarding Wizard
FRD v3.0 (FR-2.1 through FR-2.5)

Steps:
  1. Business Profile (FR-2.1)
  2. Connect Store (FR-2.2)
  3. Configure Widget (FR-2.3)
  4. Upload Knowledge Base (FR-2.4) — uses existing /api/knowledge/upload
  5. Test & Deploy / Complete (FR-2.5)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os

from app.database import get_db
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.models.user import User
from app.middleware.jwt import get_current_user

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding Wizard"])
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class BusinessProfileRequest(BaseModel):
    """Step 1: Business profile info"""
    company_name: str
    industry: Optional[str] = None
    description: Optional[str] = None
    support_email: Optional[str] = None
    timezone: Optional[str] = "UTC"


class ConnectStoreRequest(BaseModel):
    """Step 2: Store connection info"""
    store_url: str
    platform: str  # shopify, woocommerce, wix, squarespace, custom


class ConfigureWidgetRequest(BaseModel):
    """Step 3: Widget appearance settings"""
    position: Optional[str] = "bottom-right"
    theme_color: Optional[str] = "#6366f1"
    welcome_message: Optional[str] = "Hi! How can I help you today?"
    bot_name: Optional[str] = "AI Assistant"
    pre_chat_form_enabled: Optional[bool] = False
    pre_chat_fields: Optional[List[str]] = ["name", "email"]


# ═══════════════════════════════════════════════════════════════════
# HELPER: Get or validate tenant for current user
# ═══════════════════════════════════════════════════════════════════

def get_user_tenant(user: User, db: Session) -> Tenant:
    """Get the tenant associated with the current user"""
    tenant = db.query(Tenant).filter(Tenant.owner_id == user.id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenant found for this user. Please sign up first."
        )
    return tenant


# ═══════════════════════════════════════════════════════════════════
# STEP 1: Business Profile (FR-2.1)
# ═══════════════════════════════════════════════════════════════════

@router.post("/business-profile")
async def update_business_profile(
    data: BusinessProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Set business profile information.
    Updates tenant record and advances onboarding step.
    """
    tenant = get_user_tenant(current_user, db)

    tenant.name = data.company_name
    tenant.industry = data.industry
    tenant.description = data.description
    tenant.support_email = data.support_email
    tenant.timezone = data.timezone or "UTC"

    # Also update user's company name for backward compat
    current_user.company_name = data.company_name

    # Advance onboarding step
    if tenant.onboarding_step < 1:
        tenant.onboarding_step = 1
        current_user.onboarding_step = 1

    db.commit()
    db.refresh(tenant)

    return {
        "message": "Business profile saved",
        "step": 1,
        "tenant": tenant.to_dict()
    }


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Connect Store (FR-2.2)
# ═══════════════════════════════════════════════════════════════════

@router.post("/connect-store")
async def connect_store(
    data: ConnectStoreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Connect client's e-commerce store.
    Stores the URL and platform type.
    """
    tenant = get_user_tenant(current_user, db)

    # Validate platform
    valid_platforms = ["shopify", "woocommerce", "wix", "squarespace", "custom"]
    if data.platform.lower() not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
        )

    tenant.store_url = data.store_url
    tenant.store_platform = data.platform.lower()

    # Advance onboarding step
    if tenant.onboarding_step < 2:
        tenant.onboarding_step = 2
        current_user.onboarding_step = 2

    db.commit()
    db.refresh(tenant)

    return {
        "message": "Store connected",
        "step": 2,
        "tenant": tenant.to_dict()
    }


# ═══════════════════════════════════════════════════════════════════
# STEP 3: Configure Widget (FR-2.3)
# ═══════════════════════════════════════════════════════════════════

@router.post("/configure-widget")
async def configure_widget(
    data: ConfigureWidgetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 3: Configure widget appearance and behavior.
    Creates or updates the WidgetConfig record.
    """
    tenant = get_user_tenant(current_user, db)

    # Get or create widget config
    widget_config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()

    if not widget_config:
        widget_config = WidgetConfig(tenant_id=tenant.id)
        db.add(widget_config)

    # Update config
    widget_config.position = data.position or "bottom-right"
    widget_config.theme_color = data.theme_color or "#6366f1"
    widget_config.welcome_message = data.welcome_message or "Hi! How can I help you today?"
    widget_config.bot_name = data.bot_name or "AI Assistant"
    widget_config.pre_chat_form_enabled = data.pre_chat_form_enabled
    if data.pre_chat_fields:
        widget_config.set_pre_chat_fields(data.pre_chat_fields)

    # Advance onboarding step
    if tenant.onboarding_step < 3:
        tenant.onboarding_step = 3
        current_user.onboarding_step = 3

    db.commit()
    db.refresh(widget_config)

    return {
        "message": "Widget configured",
        "step": 3,
        "widget_config": widget_config.to_dict()
    }


# ═══════════════════════════════════════════════════════════════════
# STEP 4: Upload Knowledge Base (FR-2.4)
# NOTE: Uses existing /api/knowledge/upload endpoint
# This step just advances the onboarding counter
# ═══════════════════════════════════════════════════════════════════

@router.post("/upload-kb-complete")
async def mark_kb_upload_complete(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 4: Mark KB upload step as complete.
    Actual file upload uses /api/knowledge/upload separately.
    This endpoint just advances the onboarding step.
    """
    tenant = get_user_tenant(current_user, db)

    if tenant.onboarding_step < 4:
        tenant.onboarding_step = 4
        current_user.onboarding_step = 4

    db.commit()

    return {
        "message": "Knowledge base step completed",
        "step": 4
    }


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Complete Onboarding (FR-2.5)
# ═══════════════════════════════════════════════════════════════════

@router.post("/complete")
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 5: Complete the onboarding process.
    Marks tenant and user as onboarded, activates widget.
    Returns the embed code for the widget.
    """
    tenant = get_user_tenant(current_user, db)

    # Mark as complete
    tenant.onboarding_completed = True
    tenant.onboarding_step = 5
    tenant.is_active = True
    current_user.onboarding_completed = True
    current_user.onboarding_step = 5

    # Ensure widget is active
    widget_config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()
    if widget_config:
        widget_config.is_active = True

    db.commit()

    # Generate embed code
    embed_code = f'<script src="{BACKEND_URL}/widget/embed.js" data-widget-key="{tenant.widget_api_key}"></script>'

    return {
        "message": "Onboarding complete! Your widget is now active.",
        "step": 5,
        "onboarding_completed": True,
        "embed_code": embed_code,
        "widget_api_key": tenant.widget_api_key
    }


# ═══════════════════════════════════════════════════════════════════
# GET STATUS
# ═══════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current onboarding progress for the logged-in user.
    """
    tenant = get_user_tenant(current_user, db)

    widget_config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()

    return {
        "current_step": tenant.onboarding_step,
        "onboarding_completed": tenant.onboarding_completed,
        "steps": {
            "1_business_profile": tenant.onboarding_step >= 1,
            "2_connect_store": tenant.onboarding_step >= 2,
            "3_configure_widget": tenant.onboarding_step >= 3,
            "4_upload_kb": tenant.onboarding_step >= 4,
            "5_complete": tenant.onboarding_completed,
        },
        "tenant": tenant.to_dict(),
        "widget_config": widget_config.to_dict() if widget_config else None,
    }
