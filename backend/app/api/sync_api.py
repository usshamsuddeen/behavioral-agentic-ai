"""
Sync API — V5 NEW: Real-Time CSV Sync Management
Endpoints for configuring and triggering external CSV syncs.

Endpoints:
  POST   /api/sync/config             — Create/update sync config
  GET    /api/sync/configs             — List all sync configs for tenant
  DELETE /api/sync/configs/{id}        — Delete a sync config
  POST   /api/sync/trigger/{id}       — Manually trigger a sync
  GET    /api/sync/status/{id}        — Get sync status + last results
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from app.models.user import User
from app.models.sync_config import SyncConfig
from app.middleware.jwt import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["Sync (Real-Time CSV)"])


# ═══════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════

class SyncConfigRequest(BaseModel):
    """Create or update a sync configuration."""
    sync_type: str = Field(..., description="Type: 'orders' or 'products'")
    csv_url: str = Field(..., description="URL to the external CSV file")
    auth_header_name: Optional[str] = Field(None, description="Auth header name (e.g., 'Authorization')")
    auth_header_value: Optional[str] = Field(None, description="Auth header value (e.g., 'Bearer xxx')")
    sync_interval_minutes: int = Field(60, description="Sync interval: 15, 30, 60, 360, 1440")
    is_active: bool = True


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/config")
async def create_or_update_sync_config(
    request: SyncConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a sync configuration for orders or products."""
    if request.sync_type not in ("orders", "products"):
        raise HTTPException(400, "sync_type must be 'orders' or 'products'")

    if request.sync_interval_minutes not in (15, 30, 60, 360, 1440):
        raise HTTPException(400, "sync_interval_minutes must be 15, 30, 60, 360, or 1440")

    # Check if config already exists for this tenant + type
    existing = db.query(SyncConfig).filter(
        SyncConfig.tenant_id == current_user.tenant_id,
        SyncConfig.sync_type == request.sync_type,
    ).first()

    if existing:
        # Update existing
        existing.csv_url = request.csv_url
        existing.auth_header_name = request.auth_header_name
        existing.auth_header_value = request.auth_header_value
        existing.sync_interval_minutes = request.sync_interval_minutes
        existing.is_active = request.is_active
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return {"success": True, "config": existing.to_dict(), "action": "updated"}
    else:
        # Create new
        config = SyncConfig(
            tenant_id=current_user.tenant_id,
            sync_type=request.sync_type,
            csv_url=request.csv_url,
            auth_header_name=request.auth_header_name,
            auth_header_value=request.auth_header_value,
            sync_interval_minutes=request.sync_interval_minutes,
            is_active=request.is_active,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return {"success": True, "config": config.to_dict(), "action": "created"}


@router.get("/configs")
async def list_sync_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all sync configurations for the current tenant."""
    configs = db.query(SyncConfig).filter(
        SyncConfig.tenant_id == current_user.tenant_id,
    ).all()

    return {
        "configs": [c.to_dict() for c in configs],
        "total": len(configs),
    }


@router.delete("/configs/{config_id}")
async def delete_sync_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a sync configuration."""
    config = db.query(SyncConfig).filter(
        SyncConfig.id == config_id,
        SyncConfig.tenant_id == current_user.tenant_id,
    ).first()

    if not config:
        raise HTTPException(404, "Sync config not found")

    db.delete(config)
    db.commit()
    return {"success": True, "deleted_id": config_id}


@router.post("/trigger/{config_id}")
async def trigger_sync(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger a sync now."""
    config = db.query(SyncConfig).filter(
        SyncConfig.id == config_id,
        SyncConfig.tenant_id == current_user.tenant_id,
    ).first()

    if not config:
        raise HTTPException(404, "Sync config not found")

    if config.last_sync_status == "running":
        raise HTTPException(409, "Sync is already running")

    # Rate limit: minimum 2 minutes between manual triggers
    if config.last_synced_at:
        from datetime import timedelta
        if datetime.utcnow() - config.last_synced_at < timedelta(minutes=2):
            raise HTTPException(429, "Please wait at least 2 minutes between sync triggers")

    # Run sync
    from app.services.sync_service import sync_orders, sync_products

    if config.sync_type == "orders":
        result = await sync_orders(config, db)
    elif config.sync_type == "products":
        result = await sync_products(config, db)
    else:
        raise HTTPException(400, f"Unknown sync type: {config.sync_type}")

    return {
        "success": True,
        "sync_type": config.sync_type,
        "result": result,
        "config": config.to_dict(),
    }


@router.get("/status/{config_id}")
async def get_sync_status(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current status and last results for a sync config."""
    config = db.query(SyncConfig).filter(
        SyncConfig.id == config_id,
        SyncConfig.tenant_id == current_user.tenant_id,
    ).first()

    if not config:
        raise HTTPException(404, "Sync config not found")

    return {"config": config.to_dict()}
