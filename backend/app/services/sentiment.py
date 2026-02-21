"""
Sentiment Analysis Service
Production-grade implementation with 3-tier fallback:
  1. BERT Transformer (Primary) - nlptown/bert-base-multilingual-uncased-sentiment
  2. VADER (Secondary) - Fast English analysis
  3. Keywords (Tertiary) - Always works, multilingual
"""

import re
import logging
from typing import Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import transformer model (Phase 4)
try:
    from app.nlp.transformer_sentiment import (
        analyze_sentiment_transformer,
        is_model_available,
        get_model_info
    )
    HAS_TRANSFORMER = True
    logger.info("✅ Transformer sentiment module loaded")
except ImportError as e:
    HAS_TRANSFORMER = False
    logger.warning(f"⚠️ Transformer not available: {e}")

# Try to import VADER (fallback)
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader_analyzer = SentimentIntensityAnalyzer()
    HAS_VADER = True
except ImportError:
    HAS_VADER = False
    logger.warning("⚠️ VADER not found. Using keyword fallback.")

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False


# Enhanced Multilingual Dictionaries
# Organized by language with negation words
SENTIMENT_DICTS = {
    "es": {
        "positive": {"gracias", "excelente", "bueno", "feliz", "amor", "maravilloso", "perfecto", "ayuda", "bien", "contento"},
        "negative": {"enojado", "frustrado", "terrible", "malo", "odio", "inaceptable", "queja", "mal", "peor", "lento"},
        "negations": {"no", "nunca", "jamas", "tampoco", "nada"},
        "urgent": {"demanda", "abogado", "ilegal", "policia", "denuncia"}
    },
    "fr": {
        "positive": {"merci", "excellent", "bon", "heureux", "amour", "parfait", "formidable", "bien", "content"},
        "negative": {"fâché", "frustré", "terrible", "mauvais", "déteste", "inacceptable", "plainte", "mal"},
        "negations": {"ne", "pas", "jamais", "rien", "non", "aucun"},
        "urgent": {"avocat", "poursuite", "illégal", "police", "plainte"}
    },
    "de": {
        "positive": {"danke", "gut", "toll", "super", "wunderbar", "perfekt", "froh", "liebe"},
        "negative": {"wütend", "frustriert", "schrecklich", "schlecht", "hasse", "furchtbar", "mies"},
        "negations": {"nicht", "kein", "nie", "nichts", "niemand"},
        "urgent": {"anwalt", "klage", "illegal", "polizei"}
    },
    "ar": {
        "positive": {"شكرا", "ممتاز", "جيد", "سعيد", "حب", "رائع", "عظيم"},
        "negative": {"غاضب", "محبط", "سيء", "اكراه", "مرفوض", "شكوى", "فظيع"},
        "negations": {"لا", "ليس", "لم", "لن", "ما"},
        "urgent": {"محامي", "قضية", "شرطة", "قانون"}
    },
    "zh-cn": {
        "positive": {"谢谢", "好", "棒", "快乐", "爱", "优秀", "完美", "喜欢"},
        "negative": {"生气", "沮丧", "糟糕", "坏", "讨厌", "不可接受", "投诉", "差"},
        "negations": {"不", "没", "无", "非"},
        "urgent": {"律师", "起诉", "报警", "违法"}
    }
}

# Universal Urgent Keywords (English + Common threats)
# Note: removed "cancel", "refund", "review" — these are normal e-commerce
# actions, NOT urgency signals. Only keep genuine threat/escalation words.
URGENT_KEYWORDS = {
    "lawyer", "sue", "legal", "court", "attorney", "lawsuit",
    "social media", "twitter", "facebook", "instagram", "tiktok", "linkedin",
    "police", "fbi", "better business bureau", "bbb"
}

def get_sentiment_label(sentiment: str, score: float) -> str:
    """Get human readable sentiment label.
    Score is on 0.0-1.0 scale: low=negative, 0.5=neutral, high=positive.
    """
    if sentiment == "positive":
        if score > 0.85: return "Delighted"
        if score > 0.70: return "Happy"
        return "Satisfied"
    elif sentiment == "negative":
        if score < 0.10: return "Furious"
        if score < 0.20: return "Frustrated"
        if score < 0.30: return "Upset"
        return "Disappointed"
    return "Neutral"

def get_sentiment_emoji(sentiment: str, score: float) -> str:
    """Get emoji for sentiment (score: 0.0-1.0, low=neg, high=pos)"""
    if sentiment == "positive":
        return "\U0001f929" if score > 0.85 else "\U0001f60a" if score > 0.70 else "\U0001f642"
    elif sentiment == "negative":
        return "\U0001f92c" if score < 0.10 else "\U0001f621" if score < 0.20 else "\U0001f61e"
    return "\U0001f610"

def analyze_english_vader(text: str) -> Tuple[str, float]:
    """Analyze English text using VADER.
    Returns (sentiment, score) on [0, 1] scale: low=negative, 0.5=neutral, high=positive.
    """
    if not HAS_VADER:
        return analyze_english_textblob(text)
        
    scores = vader_analyzer.polarity_scores(text)
    compound = scores['compound']
    
    # Map VADER compound (-1 to 1) directly to our 0-1 scale
    # -1.0 → 0.0, 0.0 → 0.5, 1.0 → 1.0
    score = (compound + 1.0) / 2.0
    
    if compound >= 0.05:
        sentiment = "positive"
    elif compound <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"
        
    return sentiment, score

def analyze_english_textblob(text: str) -> Tuple[str, float]:
    """Analyze English text using TextBlob.
    Returns (sentiment, score) on [0, 1] scale: low=negative, 0.5=neutral, high=positive.
    """
    if not HAS_TEXTBLOB:
        return "neutral", 0.5
        
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1.0 to 1.0
    
    # Map polarity directly: -1→0, 0→0.5, 1→1.0
    score = (polarity + 1.0) / 2.0
    
    if polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"
        
    return sentiment, score

def analyze_multilingual(text: str, lang_code: str) -> Tuple[str, float]:
    """
    Analyze non-English text using enhanced keyword matching with negation
    """
    lang_data = SENTIMENT_DICTS.get(lang_code)
    
    # If language not supported, try basic English logic or return neutral
    if not lang_data:
        return "neutral", 0.5
        
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    score_sum = 0
    matches = 0
    
    # Simple window-based negation check
    for i, word in enumerate(words):
        # Check previous word for negation
        is_negated = False
        if i > 0 and words[i-1] in lang_data["negations"]:
            is_negated = True
            
        if word in lang_data["positive"]:
            val = 1 if not is_negated else -1
            score_sum += val
            matches += 1
        elif word in lang_data["negative"]:
            val = -1 if not is_negated else 0.5  # "Not bad" is slightly positive/neutral
            score_sum += val
            matches += 1
            
    if matches == 0:
        return "neutral", 0.5
        
    # Normalize score
    normalized_score = score_sum / matches  # Range: -1.0 to 1.0
    
    # Map to [0, 1] scale: -1→0, 0→0.5, 1→1.0
    mapped_score = (normalized_score + 1.0) / 2.0
    
    if normalized_score > 0.1:
        return "positive", mapped_score
    elif normalized_score < -0.1:
        return "negative", mapped_score
    else:
        return "neutral", 0.5

def analyze_sentiment(text: str, language: str = "en") -> Dict:
    """
    Main entry point for sentiment analysis.
    
    3-Tier Fallback Architecture:
      1. BERT Transformer (Primary) - Most accurate, multilingual
      2. VADER (Secondary) - Fast, English-focused
      3. Keywords (Tertiary) - Always works, all languages
    
    Args:
        text: Message text to analyze
        language: Language code (e.g., "en", "es", "fr")
        
    Returns:
        Dict with sentiment analysis results
    """
    
    # 1. Check for Urgent Keywords (Global Override - runs always)
    text_lower = text.lower()
    urgent_matches = [w for w in URGENT_KEYWORDS if w in text_lower]
    is_urgent = len(urgent_matches) > 0
    
    # 2. Add Caps Lock Detection (Frustration indicator)
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    is_shouting = caps_ratio > 0.4 and len(text) > 10
    
    # 3. Initialize defaults
    sentiment = "neutral"
    score = 0.5
    confidence = 0.5
    model_used = "keyword"
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 1: BERT Transformer (Primary - Most Accurate)
    # ═══════════════════════════════════════════════════════════════════
    if HAS_TRANSFORMER and is_model_available():
        try:
            # Transformer supports: en, de, fr, es, it, nl
            supported_langs = {"en", "de", "fr", "es", "it", "nl"}
            lang_prefix = language[:2] if language else "en"
            
            if lang_prefix in supported_langs:
                result = analyze_sentiment_transformer(text)
                
                if result.get("success", False):
                    sentiment = result["sentiment"]
                    # Use BERT score directly (already on 0-1 scale)
                    score = result["score"]
                    confidence = result["confidence"]
                    model_used = "bert-multilingual"
                    logger.debug(f"🤖 Transformer: {sentiment} ({score:.2f})")
                    
        except Exception as e:
            logger.warning(f"⚠️ Transformer failed, falling back: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 2: VADER (Secondary - Fast English Fallback)
    # ═══════════════════════════════════════════════════════════════════
    if model_used == "keyword" and language.startswith("en"):
        if HAS_VADER:
            try:
                sentiment, score = analyze_english_vader(text)
                confidence = 0.85
                model_used = "vader"
                logger.debug(f"📊 VADER: {sentiment} ({score:.2f})")
            except Exception as e:
                logger.warning(f"⚠️ VADER failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 3: Keywords (Tertiary - Always Works)
    # ═══════════════════════════════════════════════════════════════════
    if model_used == "keyword":
        try:
            if language.startswith("en"):
                sentiment, score = analyze_english_vader(text) if HAS_VADER else analyze_english_textblob(text)
            else:
                sentiment, score = analyze_multilingual(text, language)
            confidence = 0.65
            model_used = "keyword"
            logger.debug(f"🔤 Keywords: {sentiment} ({score:.2f})")
        except Exception as e:
            logger.error(f"❌ All analyzers failed: {e}")
            sentiment = "neutral"
            score = 0.5
            confidence = 0.3

    # ═══════════════════════════════════════════════════════════════════
    # POST-PROCESSING: Apply modifiers (urgency, shouting)
    # ═══════════════════════════════════════════════════════════════════
    
    # Urgency override — push score toward negative (LOW score = negative)
    if is_urgent:
        if sentiment == "positive": 
            sentiment = "neutral"
        if sentiment == "neutral": 
            sentiment = "negative"
        # For negative sentiment, score should be LOW (close to 0, not 0.85!)
        # Previous bug: score = max(score, 0.85) made negative look positive
        if sentiment == "negative":
            score = min(score, 0.15)  # Clamp to low value for negative+urgent
        
    # Shouting amplifier — push score even lower for negative sentiment
    if is_shouting and sentiment == "negative":
        score = max(score - 0.15, 0.01)  # Push further toward 0 (very negative)
        
    # ═══════════════════════════════════════════════════════════════════
    # FORMAT OUTPUT
    # ═══════════════════════════════════════════════════════════════════
    return {
        "sentiment": sentiment,
        "score": round(score, 3),
        "label": get_sentiment_label(sentiment, score),
        "emoji": get_sentiment_emoji(sentiment, score),
        "confidence": round(confidence, 2),
        "model": model_used,
        "is_urgent": is_urgent,
        "is_shouting": is_shouting,
        "language": language
    }
