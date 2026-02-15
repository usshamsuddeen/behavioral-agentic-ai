"""
Integration Models - Database models for third-party integrations
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import secrets

from app.database import Base


class Integration(Base):
    """
    Third-party integration configuration.
    Stores credentials and settings for each connected service.
    """
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Association
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(String(50), index=True, nullable=True)
    
    # Integration Info
    name = Column(String(50), nullable=False, index=True)  # whatsapp, telegram, slack, etc.
    display_name = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    status = Column(String(20), default="disconnected")  # disconnected, connecting, connected, error
    
    # Credentials (encrypted in production)
    credentials = Column(JSON, nullable=True)  # Stores tokens, API keys, etc.
    
    # Configuration
    config = Column(JSON, nullable=True)  # Integration-specific settings
    
    # Metadata
    connected_at = Column(DateTime(timezone=True), nullable=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name or self.name.title(),
            "is_active": self.is_active,
            "is_connected": self.is_connected,
            "status": self.status,
            "config": self.config,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def set_credentials(self, **kwargs):
        """Set integration credentials"""
        self.credentials = kwargs

    def get_credential(self, key: str) -> str:
        """Get a specific credential"""
        return self.credentials.get(key) if self.credentials else None

    def connect(self):
        """Mark integration as connected"""
        self.is_connected = True
        self.is_active = True
        self.status = "connected"
        self.connected_at = datetime.utcnow()
        self.error_message = None

    def disconnect(self):
        """Mark integration as disconnected"""
        self.is_connected = False
        self.is_active = False
        self.status = "disconnected"
        self.credentials = None

    def set_error(self, message: str):
        """Set error status"""
        self.status = "error"
        self.error_message = message


class WebhookEvent(Base):
    """
    Webhook event log.
    Tracks incoming webhook events for debugging and audit.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # Source
    integration_id = Column(Integer, ForeignKey("integrations.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(50), nullable=False, index=True)  # whatsapp, telegram, etc.
    
    # Event Info
    event_type = Column(String(50), nullable=True)
    event_id = Column(String(100), nullable=True, index=True)
    
    # Payload
    payload = Column(JSON, nullable=True)
    headers = Column(JSON, nullable=True)
    
    # Processing
    status = Column(String(20), default="received")  # received, processing, processed, failed
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def mark_processed(self):
        """Mark event as successfully processed"""
        self.status = "processed"
        self.processed_at = datetime.utcnow()

    def mark_failed(self, error: str):
        """Mark event as failed"""
        self.status = "failed"
        self.error_message = error


class APIKey(Base):
    """
    API Key for external access.
    Used for REST API authentication.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key info
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for display
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    
    # Permissions
    permissions = Column(JSON, default=["read"])  # read, write, admin
    
    # Rate limiting
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    @staticmethod
    def generate_key() -> tuple:
        """Generate a new API key. Returns (full_key, key_hash, prefix)"""
        import hashlib
        full_key = f"bai_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        prefix = full_key[:12]
        return full_key, key_hash, prefix

    def is_valid(self) -> bool:
        """Check if API key is valid"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def record_usage(self):
        """Record API key usage"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1
