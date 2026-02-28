"""
Retrieval Service for Behavioral Agentic AI
Implements RAG (Retrieval-Augmented Generation) retrieval logic

Features:
- Semantic search using embeddings
- Hybrid search (vector + keyword)
- Relevance scoring
- Context window management

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.ai.embeddings import get_embedding_service
from app.ai.vector_store import get_vector_store

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Container for a single retrieval result."""
    text: str
    source: str
    similarity: float
    metadata: Dict
    chunk_index: int = 0
    total_chunks: int = 1


class RetrievalService:
    """
    RAG Retrieval Service.
    
    Combines embedding-based semantic search with knowledge base
    to find relevant context for AI responses.
    
    Attributes:
        embedding_service: Text embedding service
        vector_store: Vector database interface
        default_top_k: Default number of results to retrieve
    """
    
    def __init__(self, default_top_k: int = 5, min_similarity: float = 0.3):
        """
        Initialize retrieval service.
        
        Args:
            default_top_k: Default number of results
            min_similarity: Minimum similarity threshold
        """
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.default_top_k = default_top_k
        self.min_similarity = min_similarity
    
    def retrieve(
        self,
        client_id: str,
        query: str,
        top_k: Optional[int] = None,
        doc_type: Optional[str] = None,
        category: Optional[str] = None,
        min_similarity: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            client_id: Client identifier
            query: Search query
            top_k: Number of results (default: self.default_top_k)
            doc_type: Filter by document type (product, policy, faq, etc.)
            category: Filter by category
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of RetrievalResult objects sorted by relevance
        """
        if not query or not query.strip():
            return []
        
        top_k = top_k or self.default_top_k
        min_sim = min_similarity or self.min_similarity
        
        try:
            # Build collection name based on client_id
            collection_name = f"client_{client_id}" if client_id else "default"
            
            # Search vector store using query text (it handles embedding internally)
            raw_results = self.vector_store.search(
                query=query,
                collection_name=collection_name,
                n_results=top_k + 2,  # Fetch slightly more for filtering
                min_similarity=min_sim
            )
            
            # Convert to RetrievalResult
            results = []
            for r in raw_results:
                similarity = r.get("similarity", 0.5)
                
                # Apply metadata filters if specified
                metadata = r.get("metadata", {})
                if doc_type and metadata.get("type") != doc_type:
                    continue
                if category and metadata.get("category") != category:
                    continue
                
                result = RetrievalResult(
                    text=r.get("text", ""),
                    source=metadata.get("source", "unknown"),
                    similarity=similarity,
                    metadata=metadata,
                    chunk_index=metadata.get("chunk_index", 0),
                    total_chunks=metadata.get("total_chunks", 1)
                )
                results.append(result)
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x.similarity, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"[ERROR] Retrieval failed: {e}")
            return []
    
    def retrieve_context(
        self,
        client_id: str,
        query: str,
        max_tokens: int = 2000,
        top_k: int = 5,
        doc_type: Optional[str] = None
    ) -> Tuple[str, List[RetrievalResult]]:
        """
        Retrieve and format context for LLM consumption.
        
        Args:
            client_id: Client identifier
            query: Search query
            max_tokens: Maximum approximate tokens for context
            top_k: Number of results
            doc_type: Filter by document type
            
        Returns:
            Tuple of (formatted_context_string, results_list)
        """
        results = self.retrieve(
            client_id=client_id,
            query=query,
            top_k=top_k,
            doc_type=doc_type
        )
        
        if not results:
            return "", []
        
        # Build context string with token limit
        context_parts = []
        image_urls = []  # ★ V4.1: Collect image URLs from metadata
        total_chars = 0
        char_limit = max_tokens * 4  # Approximate chars per token
        
        for i, result in enumerate(results, 1):
            text = result.text.strip()
            source = result.source
            
            # ★ V4.1: Check for image URL in chunk metadata
            if result.metadata and result.metadata.get("file_url"):
                img_url = result.metadata["file_url"]
                if img_url not in image_urls:
                    image_urls.append(img_url)
            
            # Format this chunk
            chunk = f"[Source: {source}]\n{text}\n"
            
            if total_chars + len(chunk) > char_limit:
                # Truncate if exceeding limit
                remaining = char_limit - total_chars
                if remaining > 100:
                    chunk = chunk[:remaining] + "..."
                    context_parts.append(chunk)
                break
            
            context_parts.append(chunk)
            total_chars += len(chunk)
        
        context = "\n---\n".join(context_parts)
        
        # ★ V4.1: Append image references for the LLM + widget
        if image_urls:
            context += "\n\n[RELATED_IMAGES]\n"
            for url in image_urls:
                context += f"[IMAGE:{url}]\n"
        
        return context, results
    
    def get_relevant_faqs(
        self,
        client_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Retrieve FAQ entries relevant to a query.
        
        Args:
            client_id: Client identifier
            query: User question
            top_k: Number of FAQs to return
            
        Returns:
            List of FAQ dictionaries
        """
        results = self.retrieve(
            client_id=client_id,
            query=query,
            top_k=top_k,
            doc_type="faq"
        )
        
        faqs = []
        for r in results:
            faqs.append({
                "question": r.metadata.get("question", query),
                "answer": r.text,
                "similarity": r.similarity,
                "source": r.source
            })
        
        return faqs
    
    def get_product_info(
        self,
        client_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Retrieve product information relevant to a query.
        
        Args:
            client_id: Client identifier
            query: Product query
            top_k: Number of products to return
            
        Returns:
            List of product info dictionaries
        """
        results = self.retrieve(
            client_id=client_id,
            query=query,
            top_k=top_k,
            doc_type="product"
        )
        
        products = []
        for r in results:
            products.append({
                "name": r.metadata.get("product_name", "Unknown"),
                "description": r.text,
                "category": r.metadata.get("category", ""),
                "similarity": r.similarity,
                "source": r.source
            })
        
        return products
    
    def get_policy_info(
        self,
        client_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Retrieve policy information relevant to a query.
        
        Args:
            client_id: Client identifier
            query: Policy query
            top_k: Number of results
            
        Returns:
            List of policy info dictionaries
        """
        results = self.retrieve(
            client_id=client_id,
            query=query,
            top_k=top_k,
            doc_type="policy"
        )
        
        policies = []
        for r in results:
            policies.append({
                "title": r.metadata.get("title", "Policy"),
                "content": r.text,
                "section": r.metadata.get("section", ""),
                "similarity": r.similarity,
                "source": r.source
            })
        
        return policies


# Singleton instance
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """
    Get the global retrieval service instance (singleton).
    
    Returns:
        RetrievalService instance
    """
    global _retrieval_service
    
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    
    return _retrieval_service
