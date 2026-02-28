"""
Knowledge Document Model — KB Upload Metadata Tracking
FRD v3.0 §12: knowledge_documents table
Fields: id, tenant_id, filename, doc_type, category, chunk_count, file_size, status

Provides SQL-backed metadata for documents indexed into ChromaDB.
Enables the dashboard (FR-3.4) to list, filter, and delete documents
without querying ChromaDB directly.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class KnowledgeDocument(Base):
    """
    Tracks uploaded KB documents in SQL.
    Each document maps to chunks in ChromaDB (collection: tenant_{tenant_id}).
    """
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant Isolation (FR-7.3)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant = relationship("Tenant", back_populates="knowledge_documents")

    # Document Info (FRD §12)
    filename = Column(String(500), nullable=False)
    doc_type = Column(String(50), default="general")  # product, policy, faq, general
    category = Column(String(100), default="general")
    file_size = Column(Integer, default=0)  # bytes
    file_hash = Column(String(64), nullable=True)  # SHA-256 for deduplication

    # Processing Status
    status = Column(String(20), default="processing")  # processing, indexed, failed, deleted
    chunk_count = Column(Integer, default=0)

    # ChromaDB Reference
    chromadb_doc_id = Column(String(200), nullable=True)  # ID used in ChromaDB metadata

    # Upload Context
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_message = Column(Text, nullable=True)  # If status == "failed"
    # ★ V4: Original file URL for image uploads
    file_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "category": self.category,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "uploaded_by": self.uploaded_by,
            "file_url": self.file_url,  # ★ V4
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<KnowledgeDocument {self.filename} ({self.status})>"
