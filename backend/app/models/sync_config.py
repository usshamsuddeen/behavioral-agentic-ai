"""
SyncConfig Model — V5 NEW
Stores real-time sync configuration per tenant for auto-fetching
Orders and Products from external CSV URLs.

Author: Behavioral Agentic AI Team
Version: 5.0.0
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class SyncConfig(Base):
    """Configuration for real-time CSV sync from external stores."""

    __tablename__ = "sync_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # What to sync: "orders" or "products"
    sync_type = Column(String(20), nullable=False)  # "orders" | "products"

    # Remote CSV endpoint
    csv_url = Column(Text, nullable=False)

    # Optional auth for the external CSV endpoint
    auth_header_name = Column(String(100), nullable=True)   # e.g., "Authorization", "X-API-Key"
    auth_header_value = Column(Text, nullable=True)          # e.g., "Bearer xxx", "sk-xxx"

    # Sync schedule
    sync_interval_minutes = Column(Integer, default=60)  # 15, 30, 60, 360, 1440

    # Status tracking
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), default="pending")  # success | failed | pending | running
    last_sync_message = Column(Text, nullable=True)           # Error details or stats
    last_sync_created = Column(Integer, default=0)            # Rows created in last sync
    last_sync_updated = Column(Integer, default=0)            # Rows updated in last sync

    # Optional manual column mapping override (JSON)
    column_mapping_override = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="sync_configs")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "sync_type": self.sync_type,
            "csv_url": self.csv_url,
            "auth_header_name": self.auth_header_name,
            "has_auth": bool(self.auth_header_value),
            "sync_interval_minutes": self.sync_interval_minutes,
            "is_active": self.is_active,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_message": self.last_sync_message,
            "last_sync_created": self.last_sync_created,
            "last_sync_updated": self.last_sync_updated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
