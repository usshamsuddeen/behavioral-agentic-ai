"""
Vector Store for Behavioral Agentic AI
Simple, robust vector storage with NumPy backend

Features:
- In-memory vector storage with persistence
- Cosine similarity search
- No external dependencies (ChromaDB optional)
- JSON-based persistence

Author: Behavioral Agentic AI Team
Version: 2.0.0
"""

import os
import json
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import numpy as np
from datetime import datetime

from app.ai.embeddings import get_embedding_service

# Configure logging
logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_PERSIST_DIR = os.getenv("VECTOR_STORE_DIR", "data/vector_store")


@dataclass
class Document:
    """A document stored in the vector store."""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    created_at: str


class Collection:
    """A collection of documents with embeddings."""
    
    def __init__(self, name: str, dimension: int = 384):
        self.name = name
        self.dimension = dimension
        self.documents: Dict[str, Document] = {}
        self._lock = threading.Lock()
    
    def add(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict] = None
    ):
        """Add a document to the collection."""
        with self._lock:
            doc = Document(
                id=doc_id,
                text=text,
                embedding=embedding,
                metadata=metadata or {},
                created_at=datetime.now().isoformat()
            )
            self.documents[doc_id] = doc
    
    def delete(self, doc_id: str):
        """Delete a document."""
        with self._lock:
            if doc_id in self.documents:
                del self.documents[doc_id]
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        min_similarity: float = 0.0
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents."""
        if not self.documents:
            return []
        
        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)
        
        if query_norm == 0:
            return []
        
        results = []
        for doc in self.documents.values():
            doc_vec = np.array(doc.embedding)
            doc_norm = np.linalg.norm(doc_vec)
            
            if doc_norm == 0:
                continue
            
            # Cosine similarity
            similarity = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))
            
            if similarity >= min_similarity:
                results.append((doc, similarity))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:n_results]
    
    def count(self) -> int:
        """Get document count."""
        return len(self.documents)
    
    def to_dict(self) -> Dict:
        """Serialize collection to dict."""
        return {
            "name": self.name,
            "dimension": self.dimension,
            "documents": {
                doc_id: asdict(doc) 
                for doc_id, doc in self.documents.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Collection':
        """Deserialize collection from dict."""
        collection = cls(
            name=data["name"],
            dimension=data.get("dimension", 384)
        )
        for doc_id, doc_data in data.get("documents", {}).items():
            collection.documents[doc_id] = Document(**doc_data)
        return collection


class VectorStore:
    """
    Simple vector store with NumPy-based similarity search.
    
    Uses in-memory storage with optional JSON persistence.
    Falls back gracefully if ChromaDB is unavailable.
    """
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize vector store.
        
        Args:
            persist_directory: Directory for JSON persistence
        """
        self.persist_dir = Path(persist_directory or DEFAULT_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_service = get_embedding_service()
        self.dimension = self.embedding_service.dimension
        
        self.collections: Dict[str, Collection] = {}
        self._collection_mtimes: Dict[str, float] = {}  # track JSON file mtimes
        self._lock = threading.Lock()
        
        # Load existing collections
        self._load_collections()
        
        logger.info(f"[OK] VectorStore initialized at: {self.persist_dir}")
    
    def _load_collections(self):
        """Load collections from disk."""
        for json_file in self.persist_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    collection = Collection.from_dict(data)
                    self.collections[collection.name] = collection
                    self._collection_mtimes[collection.name] = json_file.stat().st_mtime
                    logger.info(f"[OK] Loaded collection: {collection.name} ({collection.count()} docs)")
            except Exception as e:
                logger.warning(f"[WARN] Failed to load {json_file}: {e}")
    
    def _save_collection(self, name: str):
        """Save a collection to disk."""
        if name not in self.collections:
            return
        
        filepath = self.persist_dir / f"{name}.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.collections[name].to_dict(), f, indent=2)
            self._collection_mtimes[name] = filepath.stat().st_mtime
        except Exception as e:
            logger.warning(f"[WARN] Failed to save collection {name}: {e}")
    
    def _reload_if_stale(self, collection_name: str):
        """Reload a collection from disk if the JSON file has been updated externally."""
        filepath = self.persist_dir / f"{collection_name}.json"
        if not filepath.exists():
            return
        
        disk_mtime = filepath.stat().st_mtime
        cached_mtime = self._collection_mtimes.get(collection_name, 0)
        
        if disk_mtime > cached_mtime:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    collection = Collection.from_dict(data)
                    self.collections[collection_name] = collection
                    self._collection_mtimes[collection_name] = disk_mtime
                    logger.info(f"[RELOAD] Collection '{collection_name}' refreshed from disk ({collection.count()} docs)")
            except Exception as e:
                logger.warning(f"[WARN] Failed to reload {collection_name}: {e}")
    
    def get_or_create_collection(self, name: str) -> Collection:
        """Get or create a collection."""
        with self._lock:
            if name not in self.collections:
                self.collections[name] = Collection(name, self.dimension)
            return self.collections[name]
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        collection_name: str = "default",
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
            collection_name: Name of collection
            ids: Optional document IDs
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        collection = self.get_or_create_collection(collection_name)
        
        # Generate embeddings
        embeddings = self.embedding_service.embed_batch(documents)
        
        # Generate IDs if not provided
        if ids is None:
            import hashlib
            ids = [
                hashlib.md5(f"{doc[:50]}_{i}".encode()).hexdigest()[:16]
                for i, doc in enumerate(documents)
            ]
        
        # Add to collection
        for i, (doc_id, doc, emb) in enumerate(zip(ids, documents, embeddings)):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            collection.add(doc_id, doc, emb, meta)
        
        # Persist
        self._save_collection(collection_name)
        
        logger.info(f"[OK] Added {len(documents)} documents to '{collection_name}'")
        return ids
    
    def search(
        self,
        query: str,
        collection_name: str = "default",
        n_results: int = 5,
        min_similarity: float = 0.1
    ) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            collection_name: Collection to search
            n_results: Max results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of results with text, metadata, and similarity
        """
        # Reload from disk if another process updated the JSON file
        self._reload_if_stale(collection_name)
        
        if collection_name not in self.collections:
            return []
        
        query_embedding = self.embedding_service.embed_text(query)
        collection = self.collections[collection_name]
        
        results = collection.search(
            query_embedding=query_embedding,
            n_results=n_results,
            min_similarity=min_similarity
        )
        
        return [
            {
                "id": doc.id,
                "text": doc.text,
                "metadata": doc.metadata,
                "similarity": sim,
                "created_at": doc.created_at
            }
            for doc, sim in results
        ]
    
    def delete_documents(
        self,
        ids: List[str],
        collection_name: str = "default"
    ):
        """Delete documents by ID."""
        if collection_name not in self.collections:
            return
        
        collection = self.collections[collection_name]
        for doc_id in ids:
            collection.delete(doc_id)
        
        self._save_collection(collection_name)
    
    def delete_collection(self, name: str):
        """Delete an entire collection."""
        with self._lock:
            if name in self.collections:
                del self.collections[name]
                
                # Remove persisted file
                filepath = self.persist_dir / f"{name}.json"
                if filepath.exists():
                    filepath.unlink()
                
                logger.info(f"[OK] Deleted collection: {name}")
    
    def get_collection_stats(self, collection_name: str = "default") -> Dict:
        """Get collection statistics."""
        if collection_name not in self.collections:
            return {"exists": False}
        
        collection = self.collections[collection_name]
        return {
            "exists": True,
            "name": collection.name,
            "document_count": collection.count(),
            "dimension": collection.dimension
        }
    
    def list_collections(self) -> List[str]:
        """List all collection names."""
        return list(self.collections.keys())
    
    def get_info(self) -> Dict:
        """Get vector store info."""
        return {
            "backend": "numpy",
            "persist_directory": str(self.persist_dir),
            "embedding_dimension": self.dimension,
            "collection_count": len(self.collections),
            "total_documents": sum(c.count() for c in self.collections.values())
        }


# Singleton instance
_vector_store: Optional[VectorStore] = None
_store_lock = threading.Lock()


def get_vector_store(persist_directory: Optional[str] = None) -> VectorStore:
    """Get global vector store instance."""
    global _vector_store
    
    if _vector_store is None:
        with _store_lock:
            if _vector_store is None:
                _vector_store = VectorStore(persist_directory)
    
    return _vector_store
