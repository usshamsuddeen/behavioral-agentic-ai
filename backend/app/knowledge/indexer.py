"""
Knowledge Indexer for Behavioral Agentic AI
Handles embedding generation and vector store indexing

Features:
- Batch embedding generation
- Automatic chunking and indexing
- Progress tracking
- Index statistics

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.ai.embeddings import get_embedding_service
from app.ai.vector_store import get_vector_store
from app.knowledge.processor import DocumentProcessor, ProcessedDocument, DocumentChunk, get_document_processor

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class IndexingResult:
    """Result of indexing operation."""
    success: bool
    document_name: str
    chunks_indexed: int
    total_chunks: int
    document_ids: List[str]
    error: Optional[str] = None


class KnowledgeIndexer:
    """
    Knowledge base indexing service.
    
    Takes processed documents and indexes them into
    the vector store for retrieval.
    
    Attributes:
        embedding_service: Text embedding service
        vector_store: Vector database interface
        processor: Document processor
    """
    
    def __init__(self):
        """Initialize knowledge indexer."""
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.processor = get_document_processor()
    
    def index_document(
        self,
        client_id: str,
        content: bytes,
        filename: str,
        doc_type: str = "general",
        category: str = "general",
        additional_metadata: Optional[Dict] = None
    ) -> IndexingResult:
        """
        Process and index a document.
        
        Args:
            client_id: Client identifier
            content: File content as bytes
            filename: Original filename
            doc_type: Document type (product, policy, faq, general)
            category: Document category
            additional_metadata: Extra metadata
            
        Returns:
            IndexingResult with status and document IDs
        """
        try:
            # Process document
            logger.info(f"📄 Processing document: {filename}")
            processed = self.processor.process_file(
                content=content,
                filename=filename,
                doc_type=doc_type,
                category=category,
                additional_metadata=additional_metadata
            )
            
            if processed.error:
                return IndexingResult(
                    success=False,
                    document_name=filename,
                    chunks_indexed=0,
                    total_chunks=0,
                    document_ids=[],
                    error=processed.error
                )
            
            if not processed.chunks:
                return IndexingResult(
                    success=False,
                    document_name=filename,
                    chunks_indexed=0,
                    total_chunks=0,
                    document_ids=[],
                    error="No chunks extracted from document"
                )
            
            # Generate embeddings (not needed — VectorStore.add_documents does it internally)
            # But log the chunk count for verification
            logger.info(f"🔢 Preparing {len(processed.chunks)} chunks for indexing")
            texts = [chunk.text for chunk in processed.chunks]
            
            # Prepare metadata
            metadatas = [chunk.metadata for chunk in processed.chunks]
            
            # Build collection name matching retrieval convention: "client_{client_id}"
            collection_name = f"client_{client_id}" if client_id else "default"
            
            # Index in vector store
            # VectorStore.add_documents signature: (documents, metadatas, collection_name, ids)
            logger.info(f"📥 Indexing {len(texts)} chunks into collection: {collection_name}")
            doc_ids = self.vector_store.add_documents(
                documents=texts,
                metadatas=metadatas,
                collection_name=collection_name
            )
            
            logger.info(f"✅ Indexed {len(doc_ids)} chunks from {filename}")
            
            return IndexingResult(
                success=True,
                document_name=filename,
                chunks_indexed=len(doc_ids),
                total_chunks=len(processed.chunks),
                document_ids=doc_ids
            )
            
        except Exception as e:
            logger.error(f"❌ Indexing failed for {filename}: {e}")
            return IndexingResult(
                success=False,
                document_name=filename,
                chunks_indexed=0,
                total_chunks=0,
                document_ids=[],
                error=str(e)
            )
    
    def index_faqs(
        self,
        client_id: str,
        faqs: List[Dict],
        category: str = "general"
    ) -> IndexingResult:
        """
        Index FAQ data.
        
        Args:
            client_id: Client identifier
            faqs: List of FAQ dictionaries with 'question' and 'answer'
            category: FAQ category
            
        Returns:
            IndexingResult
        """
        try:
            # Process FAQs
            processed = self.processor.process_faq(
                faqs=faqs,
                filename=f"faqs_{category}.json",
                category=category
            )
            
            if not processed.chunks:
                return IndexingResult(
                    success=False,
                    document_name="faqs",
                    chunks_indexed=0,
                    total_chunks=0,
                    document_ids=[],
                    error="No valid FAQs provided"
                )
            
            # Prepare texts and metadata for indexing
            texts = [chunk.text for chunk in processed.chunks]
            metadatas = [chunk.metadata for chunk in processed.chunks]
            
            # Build collection name matching retrieval convention
            collection_name = f"client_{client_id}" if client_id else "default"
            
            # Index — VectorStore handles embeddings internally
            doc_ids = self.vector_store.add_documents(
                documents=texts,
                metadatas=metadatas,
                collection_name=collection_name
            )
            
            return IndexingResult(
                success=True,
                document_name="faqs",
                chunks_indexed=len(doc_ids),
                total_chunks=len(faqs),
                document_ids=doc_ids
            )
            
        except Exception as e:
            logger.error(f"❌ FAQ indexing failed: {e}")
            return IndexingResult(
                success=False,
                document_name="faqs",
                chunks_indexed=0,
                total_chunks=0,
                document_ids=[],
                error=str(e)
            )
    
    def index_text(
        self,
        client_id: str,
        text: str,
        source: str = "manual_entry",
        doc_type: str = "general",
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> IndexingResult:
        """
        Index raw text content.
        
        Args:
            client_id: Client identifier
            text: Text content to index
            source: Source identifier
            doc_type: Document type
            category: Category
            metadata: Additional metadata
            
        Returns:
            IndexingResult
        """
        # Convert text to bytes and process as txt
        content = text.encode("utf-8")
        
        return self.index_document(
            client_id=client_id,
            content=content,
            filename=f"{source}.txt",
            doc_type=doc_type,
            category=category,
            additional_metadata=metadata
        )
    
    def get_index_stats(self, client_id: str) -> Dict:
        """
        Get indexing statistics for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dict with stats
        """
        return self.vector_store.get_collection_stats(client_id)
    
    def delete_index(self, client_id: str) -> bool:
        """
        Delete entire index for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if successful
        """
        return self.vector_store.delete_collection(client_id)


# Singleton instance
_indexer: Optional[KnowledgeIndexer] = None


def get_knowledge_indexer() -> KnowledgeIndexer:
    """
    Get the global knowledge indexer instance.
    
    Returns:
        KnowledgeIndexer instance
    """
    global _indexer
    
    if _indexer is None:
        _indexer = KnowledgeIndexer()
    
    return _indexer
