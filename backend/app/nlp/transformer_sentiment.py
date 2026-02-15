"""
Transformer-based Sentiment Analysis Service
Production-grade implementation using nlptown/bert-base-multilingual-uncased-sentiment

Features:
- Singleton model loading (load once, reuse across requests)
- LRU caching for repeated messages (performance optimization)
- Graceful fallback to VADER/keywords if model fails
- Thread-safe inference
- Memory-efficient with lazy loading
- CPU-optimized (no GPU required)

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import os
import logging
from typing import Dict, Optional, Tuple
from functools import lru_cache
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance (singleton pattern)
_model = None
_tokenizer = None
_model_lock = threading.Lock()
_model_loaded = False
_model_load_attempted = False

# Model configuration
MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"
MAX_LENGTH = 512  # BERT max token length
CACHE_SIZE = 1000  # LRU cache size for repeated messages


def _load_model() -> bool:
    """
    Load the transformer model. Thread-safe singleton pattern.
    Returns True if model loaded successfully, False otherwise.
    """
    global _model, _tokenizer, _model_loaded, _model_load_attempted
    
    # Check if already attempted to avoid repeated failures
    if _model_load_attempted:
        return _model_loaded
    
    with _model_lock:
        # Double-check inside lock
        if _model_load_attempted:
            return _model_loaded
        
        _model_load_attempted = True
        
        try:
            logger.info("🔄 Loading BERT sentiment model...")
            
            # Import here to avoid startup delay if model not needed
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            # Set torch to use CPU (portable, no GPU dependency)
            device = torch.device("cpu")
            
            # Load tokenizer and model
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
            _model.to(device)
            _model.eval()  # Set to evaluation mode (faster, no gradients)
            
            _model_loaded = True
            logger.info("✅ BERT sentiment model loaded successfully!")
            
            # Pre-warm the model with a dummy inference
            _prewarm_model()
            
            return True
            
        except ImportError as e:
            logger.warning(f"⚠️ Transformers library not installed: {e}")
            logger.warning("📦 Run: pip install transformers torch")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to load BERT model: {e}")
            logger.info("🔄 System will use VADER fallback")
            return False


def _prewarm_model():
    """Pre-warm the model with a dummy inference to optimize first real request."""
    try:
        if _model is not None and _tokenizer is not None:
            import torch
            dummy_input = _tokenizer(
                "This is a test message",
                return_tensors="pt",
                truncation=True,
                max_length=MAX_LENGTH
            )
            with torch.no_grad():
                _model(**dummy_input)
            logger.info("🔥 Model pre-warmed successfully")
    except Exception as e:
        logger.warning(f"⚠️ Pre-warm failed (non-critical): {e}")


def is_model_available() -> bool:
    """Check if transformer model is loaded and available."""
    if not _model_load_attempted:
        return _load_model()
    return _model_loaded


@lru_cache(maxsize=CACHE_SIZE)
def _cached_inference(text: str) -> Tuple[int, float]:
    """
    Cached inference for repeated messages.
    Returns: (star_rating 1-5, confidence 0-1)
    """
    import torch
    
    # Tokenize input
    inputs = _tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_LENGTH,
        padding=True
    )
    
    # Run inference (no gradients needed)
    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits
        
    # Get probabilities using softmax
    probabilities = torch.nn.functional.softmax(logits, dim=-1)
    
    # Get predicted class (0-4 maps to 1-5 stars)
    predicted_class = torch.argmax(probabilities, dim=-1).item()
    confidence = probabilities[0][predicted_class].item()
    
    star_rating = predicted_class + 1  # Convert 0-4 to 1-5
    
    return star_rating, confidence


def analyze_sentiment_transformer(text: str) -> Dict:
    """
    Analyze sentiment using BERT transformer.
    
    Args:
        text: Message text to analyze
        
    Returns:
        Dict with sentiment analysis results:
        {
            "sentiment": "positive" | "neutral" | "negative",
            "score": float (-1.0 to 1.0),
            "confidence": float (0.0 to 1.0),
            "star_rating": int (1-5),
            "model": "bert-multilingual",
            "success": bool
        }
    """
    # Clean and validate input
    if not text or not text.strip():
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.0,
            "star_rating": 3,
            "model": "none",
            "success": False,
            "error": "Empty text"
        }
    
    # Normalize text
    text = text.strip()[:MAX_LENGTH * 4]  # Rough char limit before tokenization
    
    # Check if model is available
    if not is_model_available():
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.0,
            "star_rating": 3,
            "model": "none",
            "success": False,
            "error": "Model not available"
        }
    
    try:
        # Get cached or fresh inference
        star_rating, confidence = _cached_inference(text)
        
        # Map star rating to sentiment and score
        # 1-2 stars = negative, 3 = neutral, 4-5 = positive
        if star_rating <= 2:
            sentiment = "negative"
            # Map 1-2 to -1.0 to -0.5
            score = -1.0 + (star_rating - 1) * 0.5
        elif star_rating == 3:
            sentiment = "neutral"
            score = 0.0
        else:
            sentiment = "positive"
            # Map 4-5 to 0.5 to 1.0
            score = 0.5 + (star_rating - 4) * 0.5
        
        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "star_rating": star_rating,
            "model": "bert-multilingual",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Transformer inference failed: {e}")
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.0,
            "star_rating": 3,
            "model": "bert-multilingual",
            "success": False,
            "error": str(e)
        }


def get_model_info() -> Dict:
    """Get information about the loaded model."""
    return {
        "model_name": MODEL_NAME,
        "loaded": _model_loaded,
        "load_attempted": _model_load_attempted,
        "cache_size": CACHE_SIZE,
        "max_length": MAX_LENGTH,
        "languages_supported": ["en", "de", "fr", "es", "it", "nl"]
    }


def clear_cache():
    """Clear the LRU cache (useful for testing or memory management)."""
    _cached_inference.cache_clear()
    logger.info("🧹 Sentiment cache cleared")


# Optional: Pre-load model at import time for faster first request
# Uncomment the line below for production deployment
# _load_model()
