"""
Knowledge Manager for Behavioral Agentic AI
High-level API for managing client knowledge bases

Features:
- Document upload and management
- Knowledge base CRUD operations
- Document listing and search
- Statistics and monitoring

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import uuid

from app.knowledge.indexer import KnowledgeIndexer, IndexingResult, get_knowledge_indexer
from app.ai.retrieval import RetrievalService, get_retrieval_service

# Configure logging
logger = logging.getLogger(__name__)

# Metadata storage path
METADATA_DIR = Path("./data/knowledge_metadata")


@dataclass
class DocumentRecord:
    """Record of an indexed document."""
    id: str
    client_id: str
    filename: str
    doc_type: str
    category: str
    chunk_count: int
    chunk_ids: List[str]
    file_size: int
    created_at: str
    status: str = "indexed"
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class KnowledgeManager:
    """
    High-level knowledge base management.
    
    Provides a unified interface for uploading, searching,
    and managing knowledge base documents.
    
    Attributes:
        indexer: Knowledge indexer
        retrieval: Retrieval service
        metadata_dir: Directory for document metadata
    """
    
    def __init__(self, metadata_dir: Path = METADATA_DIR):
        """
        Initialize knowledge manager.
        
        Args:
            metadata_dir: Directory for storing document metadata
        """
        self.indexer = get_knowledge_indexer()
        self.retrieval = get_retrieval_service()
        self.metadata_dir = metadata_dir
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_client_metadata_path(self, client_id: str) -> Path:
        """Get metadata file path for a client."""
        safe_id = "".join(c if c.isalnum() or c == "_" else "_" for c in client_id)
        return self.metadata_dir / f"{safe_id}_documents.json"
    
    def _load_client_documents(self, client_id: str) -> List[DocumentRecord]:
        """Load document records for a client."""
        path = self._get_client_metadata_path(client_id)
        
        if not path.exists():
            return []
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [DocumentRecord(**doc) for doc in data]
        except Exception as e:
            logger.error(f"❌ Failed to load documents for {client_id}: {e}")
            return []
    
    def _save_client_documents(self, client_id: str, documents: List[DocumentRecord]):
        """Save document records for a client."""
        path = self._get_client_metadata_path(client_id)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                data = [asdict(doc) for doc in documents]
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Failed to save documents for {client_id}: {e}")
    
    def upload_document(
        self,
        client_id: str,
        content: bytes,
        filename: str,
        doc_type: str = "general",
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Upload and index a document.
        
        Args:
            client_id: Client identifier
            content: File content as bytes
            filename: Original filename
            doc_type: Document type
            category: Document category
            metadata: Additional metadata
            
        Returns:
            Dict with upload status
        """
        doc_id = str(uuid.uuid4())
        
        # Index the document
        result = self.indexer.index_document(
            client_id=client_id,
            content=content,
            filename=filename,
            doc_type=doc_type,
            category=category,
            additional_metadata=metadata
        )
        
        # Create document record
        record = DocumentRecord(
            id=doc_id,
            client_id=client_id,
            filename=filename,
            doc_type=doc_type,
            category=category,
            chunk_count=result.chunks_indexed,
            chunk_ids=result.document_ids,
            file_size=len(content),
            created_at=datetime.utcnow().isoformat(),
            status="indexed" if result.success else "failed",
            error=result.error,
            metadata=metadata or {}
        )
        
        # Save record
        documents = self._load_client_documents(client_id)
        documents.append(record)
        self._save_client_documents(client_id, documents)
        
        return {
            "success": result.success,
            "document_id": doc_id,
            "filename": filename,
            "chunks_created": result.chunks_indexed,
            "error": result.error
        }
    
    def upload_faqs(
        self,
        client_id: str,
        faqs: List[Dict],
        category: str = "general"
    ) -> Dict:
        """
        Upload and index FAQ data.
        
        Args:
            client_id: Client identifier
            faqs: List of FAQ dictionaries
            category: FAQ category
            
        Returns:
            Dict with upload status
        """
        result = self.indexer.index_faqs(
            client_id=client_id,
            faqs=faqs,
            category=category
        )
        
        # Create record
        record = DocumentRecord(
            id=str(uuid.uuid4()),
            client_id=client_id,
            filename=f"faqs_{category}.json",
            doc_type="faq",
            category=category,
            chunk_count=result.chunks_indexed,
            chunk_ids=result.document_ids,
            file_size=len(json.dumps(faqs)),
            created_at=datetime.utcnow().isoformat(),
            status="indexed" if result.success else "failed",
            error=result.error
        )
        
        documents = self._load_client_documents(client_id)
        documents.append(record)
        self._save_client_documents(client_id, documents)
        
        return {
            "success": result.success,
            "document_id": record.id,
            "faqs_indexed": result.chunks_indexed,
            "error": result.error
        }
    
    def list_documents(self, client_id: str) -> List[Dict]:
        """
        List all documents for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of document info dictionaries
        """
        documents = self._load_client_documents(client_id)
        
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "doc_type": doc.doc_type,
                "category": doc.category,
                "chunk_count": doc.chunk_count,
                "file_size": doc.file_size,
                "status": doc.status,
                "created_at": doc.created_at
            }
            for doc in documents
        ]
    
    def delete_document(self, client_id: str, document_id: str) -> Dict:
        """
        Delete a specific document.
        
        Args:
            client_id: Client identifier
            document_id: Document ID to delete
            
        Returns:
            Dict with deletion status
        """
        documents = self._load_client_documents(client_id)
        
        # Find document
        doc_to_delete = None
        for doc in documents:
            if doc.id == document_id:
                doc_to_delete = doc
                break
        
        if not doc_to_delete:
            return {
                "success": False,
                "error": "Document not found"
            }
        
        # Delete from vector store
        from app.ai.vector_store import get_vector_store
        vs = get_vector_store()
        
        try:
            collection_name = f"client_{client_id}" if client_id else "default"
            vs.delete_documents(ids=doc_to_delete.chunk_ids, collection_name=collection_name)
        except Exception as e:
            logger.warning(f"⚠️ Could not delete vector chunks: {e}")
        
        # Remove from records
        documents = [d for d in documents if d.id != document_id]
        self._save_client_documents(client_id, documents)
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": doc_to_delete.filename
        }
    
    def delete_all_documents(self, client_id: str) -> Dict:
        """
        Delete all documents for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict with deletion status
        """
        documents = self._load_client_documents(client_id)
        doc_count = len(documents)
        
        # Delete vector collection
        self.indexer.delete_index(client_id)
        
        # Delete metadata file
        path = self._get_client_metadata_path(client_id)
        if path.exists():
            path.unlink()
        
        return {
            "success": True,
            "documents_deleted": doc_count
        }
    
    def search_knowledge(
        self,
        client_id: str,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None
    ) -> Dict:
        """
        Search the knowledge base.
        
        Args:
            client_id: Client identifier
            query: Search query
            top_k: Number of results
            doc_type: Filter by document type
            
        Returns:
            Dict with search results
        """
        results = self.retrieval.retrieve(
            client_id=client_id,
            query=query,
            top_k=top_k,
            doc_type=doc_type
        )
        
        return {
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "text": r.text,
                    "source": r.source,
                    "similarity": round(r.similarity, 3),
                    "type": r.metadata.get("type", "unknown"),
                    "category": r.metadata.get("category", "unknown")
                }
                for r in results
            ]
        }
    
    def get_document_content(self, client_id: str, document_id: str) -> Dict:
        """
        Fetch full text content for a specific document by concatenating its chunks.
        
        Args:
            client_id: Client identifier
            document_id: Document ID
            
        Returns:
            Dict with success status and full text content
        """
        documents = self._load_client_documents(client_id)
        
        # Find document
        target_doc = None
        for doc in documents:
            if doc.id == document_id:
                target_doc = doc
                break
        
        if not target_doc:
            return {
                "success": False,
                "error": "Document not found"
            }
        
        # Fetch chunk texts from vector store
        from app.ai.vector_store import get_vector_store
        vs = get_vector_store()
        collection_name = f"client_{client_id}" if client_id else "default"
        
        chunks = vs.get_documents_by_ids(
            ids=target_doc.chunk_ids,
            collection_name=collection_name
        )
        
        # Order chunks correctly if needed. The IDs are usually generated sequentially
        # or we just concatenate them. Since we reconstruct the file, simple concatenation works.
        full_text = "\n\n".join([chunk["text"] for chunk in chunks])
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": target_doc.filename,
            "content": full_text
        }

    
    def get_knowledge_stats(self, client_id: str) -> Dict:
        """
        Get knowledge base statistics.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict with statistics
        """
        documents = self._load_client_documents(client_id)
        index_stats = self.indexer.get_index_stats(client_id)
        
        # Calculate stats
        total_docs = len(documents)
        total_chunks = sum(d.chunk_count for d in documents)
        total_size = sum(d.file_size for d in documents)
        
        by_type = {}
        for doc in documents:
            by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1
        
        return {
            "client_id": client_id,
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size,
            "documents_by_type": by_type,
            "vector_store": index_stats
        }


# Singleton instance
_manager: Optional[KnowledgeManager] = None


def get_knowledge_manager() -> KnowledgeManager:
    """
    Get the global knowledge manager instance.
    
    Returns:
        KnowledgeManager instance
    """
    global _manager
    
    if _manager is None:
        _manager = KnowledgeManager()
    
    return _manager
