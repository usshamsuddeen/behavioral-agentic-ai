"""
Transformer-based Sentiment Analysis Service
Production-grade implementation using nlptown/bert-base-multilingual-uncased-sentiment

Features:
- Singleton model loading (load once, reuse across requests)
- LRU caching for repeated messages (performance optimization)
- Emotional intensity modifiers (emoji, caps, punctuation, repetition)
- Sigmoid spread for granular 0-100% scores
- Chat-text guard for BERT misclassification on conversational text
- Thread-safe inference
- CPU-optimized (no GPU required)

Author: Behavioral Agentic AI Team
Version: 5.0.0
"""

import os
import re
import math
import random
import logging
from typing import Dict, Optional, Tuple
from functools import lru_cache
from collections import Counter
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

# ═══════════════════════════════════════════════════════════════════
# Emoji sentiment dictionaries
# ═══════════════════════════════════════════════════════════════════
POSITIVE_EMOJIS = {
    "😀", "😃", "😄", "😁", "😆", "😊", "🥰", "😍", "🤩", "😘",
    "🥺", "💕", "❤️", "💖", "💗", "💓", "👍", "👏", "🎉", "🎊",
    "✨", "🌟", "⭐", "🔥", "💯", "🙏", "😇", "🤗", "💪", "👌",
    "✅", "🥇", "🤝", "💐", "🌹", "😋", "🥳", "💝", "💞", "🫶",
}
NEGATIVE_EMOJIS = {
    "😡", "🤬", "😠", "😤", "😢", "😭", "😞", "😔", "😟", "😩",
    "😫", "🥵", "😰", "😨", "😱", "💔", "👎", "🤮", "😒", "🙄",
    "😑", "💀", "☠️", "❌", "⛔", "🚫", "😾", "👊", "🤦", "😿",
}


def _load_model() -> bool:
    """
    Load the transformer model. Thread-safe singleton pattern.
    Returns True if model loaded successfully, False otherwise.
    """
    global _model, _tokenizer, _model_loaded, _model_load_attempted
    
    if _model_load_attempted:
        return _model_loaded
    
    with _model_lock:
        if _model_load_attempted:
            return _model_loaded
        
        _model_load_attempted = True
        
        try:
            logger.info("🔄 Loading BERT sentiment model...")
            
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            device = torch.device("cpu")
            
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
            _model.to(device)
            _model.eval()
            
            _model_loaded = True
            logger.info("✅ BERT sentiment model loaded successfully!")
            
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
def _cached_inference(text: str) -> Tuple:
    """
    Cached inference for repeated messages.
    Returns: (star_rating 1-5, confidence 0-1, probabilities tuple[5])
    
    The full probability distribution enables weighted scoring
    for granular 0-100% sentiment instead of 5 fixed buckets.
    """
    import torch
    
    inputs = _tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_LENGTH,
        padding=True
    )
    
    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits
        
    probabilities = torch.nn.functional.softmax(logits, dim=-1)
    
    predicted_class = torch.argmax(probabilities, dim=-1).item()
    confidence = probabilities[0][predicted_class].item()
    
    star_rating = predicted_class + 1
    probs = tuple(probabilities[0].tolist())
    
    return star_rating, confidence, probs


# ═══════════════════════════════════════════════════════════════════
# EMOTIONAL INTENSITY HELPERS
# ═══════════════════════════════════════════════════════════════════

def _emoji_modifier(text: str) -> float:
    """Detect emoji sentiment. Returns modifier in [-0.08, +0.08]."""
    pos = sum(1 for ch in text if ch in POSITIVE_EMOJIS)
    neg = sum(1 for ch in text if ch in NEGATIVE_EMOJIS)
    if pos == 0 and neg == 0:
        return 0.0
    signal = (pos - neg) * 0.04
    return max(-0.08, min(0.08, signal))


def _punctuation_modifier(text: str, raw_score: float) -> float:
    """Exclamation/question mark intensity. Returns modifier."""
    mod = 0.0
    excl = text.count("!")
    quest = text.count("?")
    
    if excl >= 2:
        # !!! amplifies whatever direction the score leans
        direction = 1.0 if raw_score > 0.5 else -1.0
        mod += direction * min(0.06, excl * 0.012)
    
    if quest >= 3:
        # ??? suggests frustration/confusion
        mod -= min(0.04, quest * 0.008)
    
    return mod


def _caps_modifier(text: str, raw_score: float) -> float:
    """ALL CAPS amplifies emotion. Returns modifier."""
    alpha_chars = [c for c in text if c.isalpha()]
    if len(alpha_chars) < 5:
        return 0.0
    
    caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    if caps_ratio < 0.55:
        return 0.0
    
    # SHOUTING — push score further from neutral
    direction = 1.0 if raw_score > 0.5 else -1.0
    intensity = (caps_ratio - 0.55) * 0.15
    return direction * min(0.07, intensity)


def _repetition_modifier(words: list, raw_score: float) -> float:
    """Repeated words = stronger emotion. Returns modifier."""
    if len(words) < 3:
        return 0.0
    
    stop = {"the", "a", "an", "is", "it", "i", "my", "to", "and", "of",
            "in", "for", "on", "this", "that", "you", "me", "we", "so",
            "but", "or", "if", "be", "at", "do", "not", "with", "have"}
    
    counts = Counter(w for w in words if w not in stop and len(w) > 2)
    repeated = {w: c for w, c in counts.items() if c >= 2}
    
    if not repeated:
        return 0.0
    
    max_repeat = max(repeated.values())
    direction = 1.0 if raw_score > 0.5 else -1.0
    return direction * min(0.05, (max_repeat - 1) * 0.018)


def _length_confidence(word_count: int, score: float) -> float:
    """
    Short messages → soften toward neutral (less certain).
    Returns length-adjusted score.
    """
    if word_count <= 2:
        weight = 0.50    # Very short — 50% toward neutral
    elif word_count <= 4:
        weight = 0.65    # Short — 65% of signal
    elif word_count <= 8:
        weight = 0.82    # Medium — 82% of signal
    elif word_count <= 15:
        weight = 0.92    # Long — 92% of signal
    else:
        weight = 1.0     # Very long — full signal
    
    return score * weight + 0.5 * (1.0 - weight)


def _sigmoid_spread(score: float, strength: float = 1.6) -> float:
    """
    Apply a mild S-curve to stretch the mushy 40-60% middle.
    strength: 1.0 = no spread, 2.0+ = aggressive spread
    """
    centered = (score - 0.5) * 2.0  # [0,1] → [-1,1]
    # Power-based smooth spread (preserves sign)
    sign = 1.0 if centered >= 0 else -1.0
    spread = sign * abs(centered) ** (1.0 / strength)
    result = (spread + 1.0) / 2.0  # [-1,1] → [0,1]
    return max(0.01, min(0.99, result))


# ═══════════════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════

def analyze_sentiment_transformer(text: str) -> Dict:
    """
    Analyze sentiment using BERT transformer with emotional intensity modifiers.
    
    9-Stage Pipeline:
      1. BERT weighted probability score (continuous 0-1)
      2. Emoji sentiment modifier
      3. Punctuation intensity (!!!, ??? amplifiers)
      4. Caps lock amplifier (ALL CAPS = stronger)
      5. Word repetition intensity (terrible terrible = stronger)
      6. Modifier application (clamped ±0.15)
      7. Message length confidence (short = soften toward neutral)
      8. Sigmoid spread (stretches the 40-60% middle)
      9. Chat-text guard + micro-jitter
    
    Produces inch-perfect scores like 7.2%, 18.5%, 33.7%, 52.1%, 67.8%, 84.3%, 96.1%.
    """
    if not text or not text.strip():
        return {
            "sentiment": "neutral", "score": 0.5, "confidence": 0.0,
            "star_rating": 3, "model": "none", "success": False,
            "error": "Empty text"
        }
    
    text = text.strip()[:MAX_LENGTH * 4]
    
    if not is_model_available():
        return {
            "sentiment": "neutral", "score": 0.5, "confidence": 0.0,
            "star_rating": 3, "model": "none", "success": False,
            "error": "Model not available"
        }
    
    try:
        # ── STAGE 1: BERT Weighted Probability Score ──────────────────
        star_rating, raw_conf, probs = _cached_inference(text)
        
        stars = [1, 2, 3, 4, 5]
        weighted_stars = sum(p * s for p, s in zip(probs, stars))
        raw_score = (weighted_stars - 1.0) / 4.0
        raw_score = max(0.0, min(1.0, raw_score))
        
        # Confidence from probability sharpness
        max_prob = max(probs)
        confidence = max(0.0, min(1.0, (max_prob - 0.20) / 0.80))
        
        # ── STAGE 2-5: Emotional Intensity Modifiers ──────────────────
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        modifier = 0.0
        modifier += _emoji_modifier(text)
        modifier += _punctuation_modifier(text, raw_score)
        modifier += _caps_modifier(text, raw_score)
        modifier += _repetition_modifier(words, raw_score)
        
        # ── STAGE 6: Apply modifier (clamped ±0.15) ──────────────────
        modifier = max(-0.15, min(0.15, modifier))
        modified_score = max(0.0, min(1.0, raw_score + modifier))
        
        # ── STAGE 7: Message length confidence ────────────────────────
        word_count = len(words) if words else len(text.split())
        length_score = _length_confidence(word_count, modified_score)
        
        # ── STAGE 8: Sigmoid spread ───────────────────────────────────
        spread_score = _sigmoid_spread(length_score)
        
        # ── STAGE 9a: Chat-text guard ─────────────────────────────────
        needs_softening = False
        if spread_score < 0.40:
            text_stripped = text.strip()
            
            is_question = (
                text_stripped.endswith("?")
                or text_lower.startswith((
                    "what ", "how ", "do ", "does ", "can ", "could ",
                    "would ", "is ", "are ", "where ", "when ", "which ",
                    "who ", "will ", "have ", "has ", "should ", "may ",
                    "tell me", "any ", "please",
                    "was ", "wie ", "wo ", "wann ", "können ", "ist ",
                    "welch", "warum ",
                    "est-ce ", "qu'", "comment ", "où ", "quand ",
                    "quel", "pourquoi ",
                    "qué ", "cómo ", "dónde ", "cuándo ", "cuál ",
                    "por qué ",
                ))
            )
            
            greeting_words = {"hi", "hello", "hey", "hola", "good morning",
                "good afternoon", "good evening", "thanks", "thank you",
                "ok", "okay", "yes", "no", "sure", "alright", "fine",
                "i see", "got it", "understood", "bye", "goodbye"}
            is_greeting = text_lower.rstrip("!., ") in greeting_words
            
            info_keywords = ("information", "info", "details", "price",
                "cost", "how much", "available", "offer", "product",
                "service", "policy", "return", "shipping", "delivery",
                "catalog", "menu", "options", "feature")
            is_info_seeking = any(kw in text_lower for kw in info_keywords)

            action_verbs = (
                "cancel", "exchange", "help", "change", "update",
                "track", "modify", "check", "find", "looking for",
                "need", "want to", "can i", "how to"
            )
            is_action_request = any(v in text_lower for v in action_verbs)
            has_please = "please" in text_lower
            
            if is_question or is_greeting or is_info_seeking or is_action_request or has_please:
                needs_softening = True
                logger.info(
                    f"Chat guard: score {spread_score:.3f} for chat text "
                    f"(q={is_question}, g={is_greeting}, i={is_info_seeking}, "
                    f"a={is_action_request}, p={has_please}), softening"
                )
        
        if needs_softening:
            spread_score = spread_score * 0.30 + 0.50 * 0.70
            star_rating = 3
            confidence = max(0.35, confidence * 0.6)
        
        # ── STAGE 9b: Micro-jitter for natural variation ──────────────
        jitter = random.uniform(-0.012, 0.012)
        score = max(0.01, min(0.99, spread_score + jitter))
        
        # ── FINAL: Sentiment label ────────────────────────────────────
        if score >= 0.58:
            sentiment = "positive"
        elif score <= 0.42:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "star_rating": star_rating,
            "model": "bert-multilingual",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Transformer inference failed: {e}")
        return {
            "sentiment": "neutral", "score": 0.5, "confidence": 0.0,
            "star_rating": 3, "model": "bert-multilingual",
            "success": False, "error": str(e)
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
