"""
User Model - Authentication & Authorization
Behavioral Agentic AI SaaS Platform — FRD v3.0
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum
import bcrypt
import secrets
import hashlib

from app.database import Base


class UserRole(str, enum.Enum):
    """User roles for authorization — FRD v3.0 Three-Actor Model"""
    SUPER_ADMIN = "super_admin"   # Platform owner (Zone 4)
    CLIENT = "client"             # Store owner (Zone 1→2→3)
    AGENT = "agent"               # Client's team member (Zone 3 limited)
    END_CUSTOMER = "end_customer" # Store visitor via widget (Zone 6)


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class User(Base):
    """
    User model for authentication and authorization.
    Supports role-based access control (RBAC) — FRD v3.0 FR-7.1.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for migration

    # Profile - keeping 'name' for backward compatibility
    name = Column(String(100), nullable=True)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    avatar_initials = Column(String(5), default="U")
    phone = Column(String(20), nullable=True)

    # Authorization — FRD v3.0 roles
    role = Column(String(20), default=UserRole.CLIENT.value)
    status = Column(String(20), default=UserStatus.ACTIVE.value)
    is_active = Column(Boolean, default=True)

    # Multi-Tenancy — FR-7.3
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    # Company/Workspace (kept for backward compat, also in Tenant)
    company_name = Column(String(200), nullable=True)
    workspace_id = Column(String(50), nullable=True, index=True)

    # Language Preference
    preferred_language = Column(String(10), default="en")
    language_name = Column(String(50), default="English")
    language_flag = Column(String(10), default="🇺🇸")
    timezone = Column(String(50), default="UTC")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Onboarding
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    conversations = relationship("Conversation", back_populates="customer", foreign_keys="[Conversation.customer_id]")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and set the user's password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def get_display_name(self) -> str:
        """Get display name for user"""
        return self.full_name or self.name or self.email.split('@')[0]

    def get_initials(self) -> str:
        """Get user initials for avatar display"""
        display_name = self.get_display_name()
        if display_name:
            parts = display_name.split()
            if len(parts) >= 2:
                return (parts[0][0] + parts[-1][0]).upper()
            return display_name[:2].upper()
        return self.email[:2].upper()

    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.get_display_name(),
            "full_name": self.full_name or self.name,
            "avatar_url": self.avatar_url,
            "avatar_initials": self.get_initials(),
            "phone": self.phone,
            "role": self.role,
            "status": self.status,
            "is_active": self.is_active,
            "tenant_id": self.tenant_id,
            "company_name": self.company_name,
            "workspace_id": self.workspace_id,
            "preferred_language": self.preferred_language,
            "language_name": self.language_name,
            "language_flag": self.language_flag,
            "timezone": self.timezone,
            "onboarding_completed": self.onboarding_completed,
            "onboarding_step": self.onboarding_step,
            "initials": self.get_initials(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self):
        return f"<User {self.get_display_name()} ({self.email})>"


class UserSession(Base):
    """
    User session model for JWT token management.
    Tracks active sessions and enables token revocation.
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Token info
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token_hash = Column(String(255), unique=True, index=True, nullable=True)
    
    # Session metadata
    device_info = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    @staticmethod
    def generate_token_hash(token: str) -> str:
        """Generate a hash for token storage (for revocation tracking)"""
        return hashlib.sha256(token.encode()).hexdigest()

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)"""
        return self.is_active and not self.is_expired()

    def revoke(self) -> None:
        """Revoke this session"""
        self.is_active = False
        self.revoked_at = datetime.utcnow()


class UserSettings(Base):
    """
    User-specific settings and preferences.
    Stored separately for efficient updates.
    """
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # General Settings
    dark_mode = Column(Boolean, default=True)
    date_format = Column(String(20), default="DD/MM/YYYY")
    time_format = Column(String(10), default="24h")
    
    # Notification Settings
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    slack_notifications = Column(Boolean, default=False)
    daily_summary = Column(Boolean, default=True)
    
    # Sentiment Analysis Settings
    negative_threshold = Column(Integer, default=65)
    frustration_sensitivity = Column(Integer, default=75)
    emotion_timeline = Column(Boolean, default=True)
    cultural_awareness = Column(Boolean, default=True)
    
    # Escalation Settings
    auto_escalation_threshold = Column(Integer, default=85)
    escalation_keywords = Column(Text, default="lawyer,manager,sue,refund,complaint")
    repeated_contact_escalation = Column(Boolean, default=True)
    vip_auto_escalation = Column(Boolean, default=False)
    
    # Language Settings
    primary_language = Column(String(10), default="en")
    enabled_languages = Column(Text, default="en,es,fr,de,zh,ar")
    auto_detect_language = Column(Boolean, default=True)
    
    # API Settings
    api_enabled = Column(Boolean, default=True)
    webhook_enabled = Column(Boolean, default=False)
    webhook_url = Column(String(500), nullable=True)
    api_key = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships  
    user = relationship("User", back_populates="settings")

    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return {
            "dark_mode": self.dark_mode,
            "date_format": self.date_format,
            "time_format": self.time_format,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
            "slack_notifications": self.slack_notifications,
            "daily_summary": self.daily_summary,
            "negative_threshold": self.negative_threshold,
            "frustration_sensitivity": self.frustration_sensitivity,
            "emotion_timeline": self.emotion_timeline,
            "cultural_awareness": self.cultural_awareness,
            "auto_escalation_threshold": self.auto_escalation_threshold,
            "escalation_keywords": self.escalation_keywords.split(",") if self.escalation_keywords else [],
            "repeated_contact_escalation": self.repeated_contact_escalation,
            "vip_auto_escalation": self.vip_auto_escalation,
            "primary_language": self.primary_language,
            "enabled_languages": self.enabled_languages.split(",") if self.enabled_languages else [],
            "auto_detect_language": self.auto_detect_language,
            "api_enabled": self.api_enabled,
            "webhook_enabled": self.webhook_enabled,
            "webhook_url": self.webhook_url,
        }

    def update_from_dict(self, data: dict) -> None:
        """Update settings from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                if key in ["escalation_keywords", "enabled_languages"] and isinstance(value, list):
                    value = ",".join(value)
                setattr(self, key, value)
