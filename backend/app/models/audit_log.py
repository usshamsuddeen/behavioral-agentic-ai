"""
Audit Log Model — System Event Logging
FRD v3.0 §12: audit_logs table
Fields: id, user_id, tenant_id, action, endpoint, status_code, timestamp

Powers FR-4.3 (Global Audit Logs) in the Super Admin panel.
Logs every significant system event: API calls, auth events, admin actions.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime

from app.database import Base


class AuditLog(Base):
    """
    System audit log entry.
    Captures API calls, auth events, and admin actions.
    Queried by Super Admin (FR-4.3) for monitoring and compliance.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who (nullable — some events are system-generated)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # What (FRD §12)
    action = Column(String(100), nullable=False, index=True)  # login, signup, upload_document, escalation, etc.
    endpoint = Column(String(500), nullable=True)  # /api/auth/login, /api/knowledge/upload, etc.
    method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE, PATCH

    # Result
    status_code = Column(Integer, nullable=True)  # HTTP status code
    error_message = Column(Text, nullable=True)  # Error details if failed

    # Context
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_body_preview = Column(String(500), nullable=True)  # First 500 chars (no secrets)
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds

    # Timestamp (FRD §12)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "ip_address": self.ip_address,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id} at {self.timestamp}>"
