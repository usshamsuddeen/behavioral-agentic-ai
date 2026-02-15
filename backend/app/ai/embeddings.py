"""
Embedding Service for Behavioral Agentic AI
Converts text to vector embeddings using multiple providers

Features:
- Google Gemini Embedding API (primary)
- Sentence-transformers (fallback if available)
- TF-IDF based embeddings (final fallback)
- Batch processing support
- Graceful degradation

Author: Behavioral Agentic AI Team
Version: 2.0.0
"""

import os
import logging
import threading
import hashlib
from typing import List, Optional, Tuple, Dict
from functools import lru_cache
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration
EMBEDDING_DIMENSION = 768  # Gemini embedding dimension
FALLBACK_DIMENSION = 384   # TF-IDF dimension
CACHE_SIZE = 500

# Global state
_embedding_provider = None
_provider_name = "none"
_initialized = False
_init_lock = threading.Lock()


class GeminiEmbeddings:
    """Google Gemini Embedding API provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.dimension = 768
        self._client = None
        self._model = "models/text-embedding-004"
    
    def _get_client(self):
        """Lazy-load Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("[OK] Gemini embeddings client initialized")
            except ImportError:
                # Try legacy package
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    self._client = genai
                    logger.info("[OK] Legacy Gemini embeddings initialized")
                except Exception as e:
                    logger.warning(f"[WARN] Gemini embeddings unavailable: {e}")
                    return None
        return self._client
    
    def embed_text(self, text: str) -> List[float]:
        """Embed single text using Gemini API."""
        client = self._get_client()
        if client is None:
            return None
        
        try:
            # New google-genai package
            if hasattr(client, 'models'):
                result = client.models.embed_content(
                    model=self._model,
                    contents=text
                )
                return result.embeddings[0].values
            else:
                # Legacy package
                result = client.embed_content(
                    model=self._model,
                    content=text
                )
                return result['embedding']
        except Exception as e:
            logger.warning(f"[WARN] Gemini embed failed: {e}")
            return None
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        results = []
        for text in texts:
            emb = self.embed_text(text)
            if emb is not None:
                results.append(emb)
            else:
                results.append([0.0] * self.dimension)
        return results


class SentenceTransformerEmbeddings:
    """Sentence-transformers based embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384
        self._model = None
    
    def _get_model(self):
        """Lazy-load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self.dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"[OK] SentenceTransformer loaded: {self.model_name}")
            except Exception as e:
                logger.warning(f"[WARN] SentenceTransformer unavailable: {e}")
                return None
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """Embed single text."""
        model = self._get_model()
        if model is None:
            return None
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"[WARN] Embed failed: {e}")
            return None
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        model = self._get_model()
        if model is None:
            return None
        try:
            embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
            return embeddings.tolist()
        except Exception:
            return None


class TFIDFEmbeddings:
    """
    Lightweight TF-IDF based embeddings (no ML dependencies).
    Works everywhere, no GPU/C++ required.
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._vocabulary: Dict[str, int] = {}
        self._vocab_lock = threading.Lock()
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return [t for t in text.split() if len(t) > 2]
    
    def _get_token_index(self, token: str) -> int:
        """Get consistent index for a token using hash."""
        return int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dimension
    
    def embed_text(self, text: str) -> List[float]:
        """Create TF-IDF-like embedding."""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dimension
        
        # Create sparse vector
        vector = [0.0] * self.dimension
        token_counts = {}
        
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        
        # Fill vector with TF values (normalized)
        max_count = max(token_counts.values())
        for token, count in token_counts.items():
            idx = self._get_token_index(token)
            tf = count / max_count  # Normalized TF
            vector[idx] = max(vector[idx], tf)  # Keep highest if collision
        
        # Normalize the vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = (np.array(vector) / norm).tolist()
        
        return vector
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        return [self.embed_text(t) for t in texts]


class EmbeddingService:
    """
    Unified embedding service with multiple providers.
    
    Provider priority:
    1. Google Gemini Embedding API (if API key available)
    2. Sentence-transformers (if installed and working)
    3. TF-IDF embeddings (always available, no dependencies)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._providers = []
        self._active_provider = None
        self._dimension = 384
        self._init_providers()
    
    def _init_providers(self):
        """Initialize available providers in priority order."""
        # 1. Try Gemini embeddings
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key:
            gemini = GeminiEmbeddings(api_key)
            # Test if it works (quick test)
            try:
                test_result = gemini.embed_text("test")
                if test_result and len(test_result) > 100:
                    self._active_provider = gemini
                    self._dimension = gemini.dimension
                    logger.info("[OK] Using Gemini embeddings (primary)")
                    return
            except Exception as e:
                logger.warning(f"[WARN] Gemini embed test failed: {e}")
        
        # 2. Try sentence-transformers
        st_embeddings = SentenceTransformerEmbeddings(self.model_name)
        try:
            test_result = st_embeddings.embed_text("test")
            if test_result and len(test_result) > 100:
                self._active_provider = st_embeddings
                self._dimension = st_embeddings.dimension
                logger.info("[OK] Using SentenceTransformer embeddings")
                return
        except Exception as e:
            logger.warning(f"[WARN] SentenceTransformer test failed: {e}")
        
        # 3. Fallback to TF-IDF (always works)
        self._active_provider = TFIDFEmbeddings(dimension=384)
        self._dimension = 384
        logger.info("[OK] Using TF-IDF embeddings (fallback)")
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
    
    def embed_text(self, text: str) -> List[float]:
        """
        Convert text to vector embedding.
        
        Args:
            text: Input text
            
        Returns:
            List of floats (embedding vector)
        """
        if not text or not text.strip():
            return [0.0] * self._dimension
        
        text = text.strip()[:8000]  # Limit length
        
        try:
            result = self._active_provider.embed_text(text)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"[WARN] Primary embed failed: {e}")
        
        # Fallback to TF-IDF
        fallback = TFIDFEmbeddings(self._dimension)
        return fallback.embed_text(text)
    
    def embed_batch(self, texts: List[str], show_progress: bool = False) -> List[List[float]]:
        """
        Batch embed multiple texts.
        
        Args:
            texts: List of texts
            show_progress: Show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        cleaned = [t.strip()[:8000] if t else "" for t in texts]
        
        try:
            result = self._active_provider.embed_batch(cleaned)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"[WARN] Batch embed failed: {e}")
        
        # Fallback
        fallback = TFIDFEmbeddings(self._dimension)
        return fallback.embed_batch(cleaned)
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        emb1 = np.array(self.embed_text(text1))
        emb2 = np.array(self.embed_text(text2))
        
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(emb1, emb2) / (norm1 * norm2))
    
    def find_most_similar(
        self, 
        query: str, 
        candidates: List[str], 
        top_k: int = 3
    ) -> List[Tuple[int, str, float]]:
        """Find most similar texts from candidates."""
        if not candidates:
            return []
        
        query_emb = np.array(self.embed_text(query))
        candidate_embs = np.array(self.embed_batch(candidates))
        
        similarities = []
        for i, emb in enumerate(candidate_embs):
            norm1 = np.linalg.norm(query_emb)
            norm2 = np.linalg.norm(emb)
            if norm1 > 0 and norm2 > 0:
                sim = float(np.dot(query_emb, emb) / (norm1 * norm2))
            else:
                sim = 0.0
            similarities.append((i, candidates[i], sim))
        
        similarities.sort(key=lambda x: x[2], reverse=True)
        return similarities[:top_k]
    
    def get_model_info(self) -> dict:
        """Get embedding service info."""
        provider_name = type(self._active_provider).__name__
        return {
            "provider": provider_name,
            "dimension": self._dimension,
            "model_name": self.model_name
        }


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None
_service_lock = threading.Lock()


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    
    if _embedding_service is None:
        with _service_lock:
            if _embedding_service is None:
                _embedding_service = EmbeddingService()
    
    return _embedding_service


def is_model_available() -> bool:
    """Check if embedding service is available (always True with fallback)."""
    return True
