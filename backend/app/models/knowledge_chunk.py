"""
KnowledgeChunk — SQLite backup for vector store chunks.

Every chunk indexed into the NumPy vector store is ALSO saved here.
On startup, if the JSON vector files are missing (e.g. after a Docker
volume wipe by Coolify), the vector store is automatically rebuilt
from these rows — zero data loss regardless of any deployment change.

Table: knowledge_chunks
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class KnowledgeChunk(Base):
    """
    One row = one chunk that lives in the NumPy vector store.
    The `embedding_json` column stores the serialized float list so the
    vector store can be rebuilt without re-running the embedding model.
    """
    __tablename__ = "knowledge_chunks"

    id            = Column(Integer, primary_key=True, index=True)

    # Tenant isolation — same key used as ChromaDB/VectorStore collection name
    collection_name = Column(String(100), nullable=False, index=True)   # = str(tenant.id)
    doc_id          = Column(String(200), nullable=False, index=True)   # vector store doc id

    # Content
    text            = Column(Text, nullable=False)
    embedding_json  = Column(Text, nullable=False)   # JSON array of floats
    metadata_json   = Column(Text, nullable=True)    # JSON object

    # Optional link back to KnowledgeDocument row
    knowledge_document_id = Column(
        Integer,
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_kchunk_collection_docid", "collection_name", "doc_id", unique=True),
    )

    def __repr__(self):
        return f"<KnowledgeChunk collection={self.collection_name} doc={self.doc_id[:16]}>"
