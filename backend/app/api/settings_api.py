"""
Settings API — Zone 3: Settings & Team Management
FRD v3.0 (FR-3.6)

Endpoints for user profile, tenant settings, team management, and API key management.
All endpoints require JWT authentication and are tenant-scoped.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserSettings, UserRole
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.middleware.jwt import get_current_user, get_tenant_for_user, require_role

router = APIRouter(prefix="/api/settings", tags=["Settings"])


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    preferred_language: Optional[str] = None


class UpdateTenantRequest(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    store_url: Optional[str] = None
    support_email: Optional[str] = None
    description: Optional[str] = None
    timezone: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    """FR-3.6.3: AI behavior settings"""
    dark_mode: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    daily_summary: Optional[bool] = None
    negative_threshold: Optional[int] = None
    frustration_sensitivity: Optional[int] = None
    auto_escalation_threshold: Optional[int] = None
    escalation_keywords: Optional[List[str]] = None
    auto_detect_language: Optional[bool] = None
    primary_language: Optional[str] = None
    enabled_languages: Optional[List[str]] = None


class UpdateRestrictionsRequest(BaseModel):
    """AI Restrictions / Rules — stored in tenant.ai_restrictions, injected into LLM system prompt"""
    restrictions: str = ""


class InviteTeamMemberRequest(BaseModel):
    """FR-3.6.5: Team member invitation"""
    email: str
    name: str
    role: str = "agent"  # agent or client


# ═══════════════════════════════════════════════════════════════════
# FR-3.6.1: Get All Settings
# ═══════════════════════════════════════════════════════════════════

@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    FR-3.6.1–FR-3.6.7: Get complete settings view.
    Returns user profile, tenant info, user settings, widget config, and API key.
    """
    tenant = get_tenant_for_user(current_user, db)
    
    # Get user settings (auto-create if missing)
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Get widget config
    widget_config = None
    if tenant:
        widget_config = db.query(WidgetConfig).filter(
            WidgetConfig.tenant_id == tenant.id
        ).first()
    
    # Get team members — FR-3.6.5
    team_members = []
    if tenant:
        members = db.query(User).filter(
            User.tenant_id == tenant.id,
            User.id != current_user.id
        ).all()
        team_members = [
            {
                "id": m.id,
                "name": m.get_display_name(),
                "email": m.email,
                "role": m.role,
                "status": m.status,
                "last_login": m.last_login.isoformat() if m.last_login else None,
                "avatar_initials": m.get_initials()
            }
            for m in members
        ]
    
    return {
        "profile": current_user.to_dict(),
        "tenant": {
            "id": tenant.id,
            "business_name": tenant.name,
            "business_type": tenant.industry,
            "description": tenant.description,
            "store_url": tenant.store_url,
            "store_platform": tenant.store_platform,
            "support_email": tenant.support_email,
            "timezone": tenant.timezone,
            "status": "active" if getattr(tenant, 'is_active', True) else "suspended",
            "onboarding_completed": tenant.onboarding_completed,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None
        } if tenant else None,
        "settings": settings.to_dict() if settings else {},
        "widget": {
            "is_active": widget_config.is_active if widget_config else False,
            "theme_color": widget_config.theme_color if widget_config else "#6366f1",
            "bot_name": widget_config.bot_name if widget_config else "AI Assistant",
            "welcome_message": widget_config.welcome_message if widget_config else "Hello! How can I help?",
            "position": widget_config.position if widget_config else "bottom-right"
        } if widget_config else None,
        "api_key": {
            "key": tenant.widget_api_key if tenant else None,
            "is_active": tenant.is_active if tenant else False
        } if tenant else None,
        "team": team_members
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.6.1: Update Profile
# ═══════════════════════════════════════════════════════════════════

@router.put("/profile")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.6.1: Update user profile information"""
    if data.full_name is not None:
        current_user.full_name = data.full_name
        current_user.name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.timezone is not None:
        current_user.timezone = data.timezone
    if data.preferred_language is not None:
        current_user.preferred_language = data.preferred_language
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Profile updated successfully",
        "profile": current_user.to_dict()
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.6.2: Update Tenant/Business Info
# ═══════════════════════════════════════════════════════════════════

@router.put("/tenant")
async def update_tenant(
    data: UpdateTenantRequest,
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """FR-3.6.2: Update tenant/business information"""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    if data.business_name is not None:
        tenant.name = data.business_name
    if data.business_type is not None:
        tenant.industry = data.business_type
    if data.store_url is not None:
        tenant.store_url = data.store_url
    if data.support_email is not None:
        tenant.support_email = data.support_email
    if data.description is not None:
        tenant.description = data.description
    if data.timezone is not None:
        tenant.timezone = data.timezone
    
    tenant.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Tenant settings updated successfully",
        "tenant_id": tenant.id
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.6.3: Update AI Behavior Settings
# ═══════════════════════════════════════════════════════════════════

@router.put("/preferences")
async def update_settings(
    data: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.6.3: Update AI behavior and notification settings"""
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Update from the request data
    update_data = data.dict(exclude_none=True)
    settings.update_from_dict(update_data)
    
    db.commit()
    db.refresh(settings)
    
    return {
        "message": "Settings updated successfully",
        "settings": settings.to_dict()
    }


# ═══════════════════════════════════════════════════════════════════
# AI Restrictions / Rules — stored in tenant.ai_restrictions
# Automatically injected into LLM system prompt via company_guidelines
# ═══════════════════════════════════════════════════════════════════

@router.get("/restrictions")
async def get_restrictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI restrictions/rules for this tenant."""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    return {
        "restrictions": tenant.ai_restrictions or "",
        "tenant_id": tenant.id
    }


@router.put("/restrictions")
async def update_restrictions(
    data: UpdateRestrictionsRequest,
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Save AI restrictions/rules for this tenant.
    Stored in tenant.ai_restrictions → piped to LLM as GUIDELINES in system prompt.
    """
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    tenant.ai_restrictions = data.restrictions.strip()
    tenant.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Restrictions saved successfully",
        "restrictions": tenant.ai_restrictions,
        "tenant_id": tenant.id
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.6.5: Invite Team Member
# ═══════════════════════════════════════════════════════════════════

@router.post("/invite-team")
async def invite_team_member(
    data: InviteTeamMemberRequest,
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """FR-3.6.5: Invite a team member to the tenant"""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    
    # Validate role
    if data.role not in ("agent", "client"):
        raise HTTPException(status_code=400, detail="Role must be 'agent' or 'client'")
    
    # Create the invited user with pending status
    new_user = User(
        email=data.email,
        full_name=data.name,
        name=data.name,
        role=data.role,
        status="pending",
        is_active=True,
        tenant_id=tenant.id,
        company_name=tenant.business_name,
        avatar_initials=data.name[:2].upper() if data.name else "U"
    )
    
    # Set a temporary random password (user will reset via email)
    import secrets
    temp_password = secrets.token_urlsafe(16)
    new_user.set_password(temp_password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": f"Team member {data.name} invited successfully",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.get_display_name(),
            "role": new_user.role,
            "status": "pending"
        }
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.6.7: Regenerate Widget API Key
# ═══════════════════════════════════════════════════════════════════

@router.post("/regenerate-key")
async def regenerate_api_key(
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """FR-3.6.7: Regenerate the widget API key for the tenant"""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    # Generate new API key
    old_key_prefix = tenant.widget_api_key[:8] if tenant.widget_api_key else "none"
    tenant.widget_api_key = Tenant.generate_api_key()
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "API key regenerated successfully",
        "old_key_prefix": old_key_prefix + "...",
        "new_key": tenant.widget_api_key
    }


# ═══════════════════════════════════════════════════════════════════
# Remove Team Member
# ═══════════════════════════════════════════════════════════════════

@router.delete("/team/{user_id}")
async def remove_team_member(
    user_id: int,
    current_user: User = Depends(require_role(["client", "super_admin", "admin"])),
    db: Session = Depends(get_db)
):
    """Remove a team member from the tenant"""
    tenant = get_tenant_for_user(current_user, db)
    if not tenant:
        raise HTTPException(status_code=404, detail="No tenant found")
    
    # Find the team member
    member = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant.id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    if member.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the team")
    
    # Deactivate the user
    member.is_active = False
    member.status = "inactive"
    db.commit()
    
    return {
        "message": f"Team member {member.get_display_name()} removed successfully",
        "user_id": user_id
    }
