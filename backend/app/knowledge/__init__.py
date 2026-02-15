"""
Knowledge Module for Behavioral Agentic AI
Contains document processing, indexing, and management components
"""

from app.knowledge.processor import DocumentProcessor, get_document_processor
from app.knowledge.indexer import KnowledgeIndexer, get_knowledge_indexer
from app.knowledge.manager import KnowledgeManager, get_knowledge_manager

__all__ = [
    "DocumentProcessor",
    "get_document_processor", 
    "KnowledgeIndexer",
    "get_knowledge_indexer",
    "KnowledgeManager",
    "get_knowledge_manager"
]
