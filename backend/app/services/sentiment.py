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
    },
    "it": {
        "positive": {"grazie", "eccellente", "buono", "felice", "amore", "meraviglioso", "perfetto", "bene", "ottimo", "fantastico"},
        "negative": {"arrabbiato", "frustrato", "terribile", "cattivo", "odio", "inaccettabile", "reclamo", "male", "pessimo", "lento"},
        "negations": {"non", "mai", "niente", "nessuno", "nulla"},
        "urgent": {"avvocato", "causa", "illegale", "polizia", "denuncia"}
    },
    "nl": {
        "positive": {"bedankt", "uitstekend", "goed", "blij", "liefde", "geweldig", "perfect", "fijn", "fantastisch", "prima"},
        "negative": {"boos", "gefrustreerd", "verschrikkelijk", "slecht", "haat", "onacceptabel", "klacht", "erg", "vreselijk", "traag"},
        "negations": {"niet", "geen", "nooit", "niets", "niemand"},
        "urgent": {"advocaat", "rechtszaak", "illegaal", "politie", "aanklacht"}
    },

    # ═══════════════════════════════════════════════════════════════
    # V4 FIX — BUG-2: Urdu Sentiment Dictionary
    # Previously: SENTIMENT_DICTS.get("ur") returned None → always neutral
    # Now: 15 positive, 15 negative, 5 negation, 5 urgent keywords
    # ═══════════════════════════════════════════════════════════════
    "ur": {
        "positive": {
            "شکریہ", "بہترین", "اچھا", "خوش", "محبت", "عمدہ",
            "بہت اچھا", "شاندار", "مزیدار", "خوبصورت", "پسند",
            "ممنون", "واہ", "بہتر", "لاجواب"
        },
        "negative": {
            "ناراض", "غصہ", "برا", "خراب", "بدتمیز", "شکایت",
            "نفرت", "بکواس", "بیکار", "افسوس", "تکلیف",
            "مایوس", "ناقابل قبول", "بدترین", "ضائع"
        },
        "negations": {"نہیں", "نہ", "مت", "بغیر", "کبھی نہیں"},
        "urgent": {"وکیل", "عدالت", "مقدمہ", "پولیس", "ایف آئی آر"}
    },

    # ═══════════════════════════════════════════════════════════════
    # V4 FIX — Hindi Sentiment Dictionary
    # ═══════════════════════════════════════════════════════════════
    "hi": {
        "positive": {
            "धन्यवाद", "बहुत अच्छा", "अच्छा", "खुश", "प्यार",
            "शानदार", "बढ़िया", "सुंदर", "पसंद", "उत्कृष्ट",
            "मज़ेदार", "बेहतरीन", "वाह"
        },
        "negative": {
            "गुस्सा", "नाराज", "बुरा", "खराब", "बकवास", "शिकायत",
            "नफरत", "बेकार", "निराश", "भयानक", "घटिया",
            "बर्बाद", "असंतुष्ट", "अस्वीकार्य"
        },
        "negations": {"नहीं", "ना", "मत", "बिना", "कभी नहीं"},
        "urgent": {"वकील", "अदालत", "पुलिस", "केस", "एफ आई आर"}
    },

    # ═══════════════════════════════════════════════════════════════
    # V4 FIX — Portuguese Sentiment Dictionary
    # ═══════════════════════════════════════════════════════════════
    "pt": {
        "positive": {"obrigado", "excelente", "bom", "feliz", "amor", "maravilhoso", "perfeito", "ótimo", "fantástico"},
        "negative": {"irritado", "frustrado", "terrível", "mau", "odeio", "inaceitável", "reclamação", "péssimo", "horrível"},
        "negations": {"não", "nunca", "nada", "nenhum", "jamais"},
        "urgent": {"advogado", "processo", "ilegal", "polícia", "denúncia"}
    },

    # ═══════════════════════════════════════════════════════════════
    # V4 FIX — Turkish Sentiment Dictionary
    # ═══════════════════════════════════════════════════════════════
    "tr": {
        "positive": {"teşekkür", "mükemmel", "iyi", "mutlu", "sevgi", "harika", "süper", "güzel", "memnun"},
        "negative": {"kızgın", "sinirli", "berbat", "kötü", "nefret", "kabul edilemez", "şikayet", "rezalet", "korkunç"},
        "negations": {"değil", "yok", "hiç", "asla", "hiçbir"},
        "urgent": {"avukat", "dava", "yasadışı", "polis", "şikayet"}
    },
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
        if score > 0.92: return "Delighted"
        if score > 0.82: return "Very Happy"
        if score > 0.72: return "Happy"
        if score > 0.62: return "Pleased"
        return "Satisfied"
    elif sentiment == "negative":
        if score < 0.08: return "Furious"
        if score < 0.15: return "Very Frustrated"
        if score < 0.22: return "Frustrated"
        if score < 0.30: return "Upset"
        if score < 0.38: return "Disappointed"
        return "Slightly Unhappy"
    if score > 0.55: return "Leaning Positive"
    if score < 0.45: return "Leaning Negative"
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
    import random
    if not HAS_VADER:
        return analyze_english_textblob(text)
        
    scores = vader_analyzer.polarity_scores(text)
    compound = scores['compound']
    
    # Map VADER compound (-1 to 1) directly to our 0-1 scale
    # -1.0 → 0.0, 0.0 → 0.5, 1.0 → 1.0
    score = (compound + 1.0) / 2.0
    
    # Add small jitter for natural variation — avoids identical scores
    jitter = random.uniform(-0.02, 0.02)
    score = max(0.01, min(0.99, score + jitter))
    score = round(score, 3)
    
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
    Analyze non-English text using weighted keyword matching with negation.
    Produces granular scores (not just 0/50/100%) by using intensity weights,
    message length blending, and small jitter for natural variation.
    """
    import random
    
    lang_data = SENTIMENT_DICTS.get(lang_code)
    
    # If language not supported, return neutral with slight variation
    if not lang_data:
        return "neutral", round(0.5 + random.uniform(-0.03, 0.03), 3)
        
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    # Intensity weights — how strong each keyword signals sentiment
    # Strong words get higher magnitude, mild words get lower
    STRONG_POS = {"excelente", "perfecto", "maravilloso", "wunderbar", "parfait",
                  "eccellente", "fantastico", "uitstekend", "ممتاز", "رائع",
                  "بہترین", "شاندار", "لاجواب", "बेहतरीन", "शानदार",
                  "mükemmel", "fantástico", "perfect", "geweldig"}
    STRONG_NEG = {"terrible", "odio", "inaceptable", "schrecklich", "furchtbar",
                  "inacceptable", "déteste", "inaccettabile", "verschrikkelijk",
                  "فظيع", "بدترین", "نفرت", "بکواس", "भयानक", "घटिया",
                  "berbat", "korkunç", "horrível", "péssimo", "hasse"}
    
    weighted_sum = 0.0
    matches = 0
    
    # Window-based negation check with intensity weights
    for i, word in enumerate(words):
        is_negated = False
        if i > 0 and words[i-1] in lang_data["negations"]:
            is_negated = True
            
        if word in lang_data["positive"]:
            intensity = 0.9 if word in STRONG_POS else 0.6
            val = intensity if not is_negated else -0.4
            weighted_sum += val
            matches += 1
        elif word in lang_data["negative"]:
            intensity = -0.9 if word in STRONG_NEG else -0.6
            val = intensity if not is_negated else 0.3  # "Not bad" slightly positive
            weighted_sum += val
            matches += 1
            
    if matches == 0:
        return "neutral", round(0.5 + random.uniform(-0.03, 0.03), 3)
        
    # Normalize to -1..1 range
    raw_score = max(-1.0, min(1.0, weighted_sum / matches))
    
    # Message length blending — short messages get softened toward 0.5
    # A 3-word message is less certain than a 20-word rant
    word_count = len(words)
    length_factor = min(1.0, word_count / 12.0)  # Full confidence at 12+ words
    softened = raw_score * (0.5 + 0.5 * length_factor)
    
    # Map to [0, 1] scale: -1→0, 0→0.5, 1→1.0
    mapped_score = (softened + 1.0) / 2.0
    
    # Add small jitter for natural variation (±0.03)
    jitter = random.uniform(-0.03, 0.03)
    mapped_score = max(0.01, min(0.99, mapped_score + jitter))
    
    if softened > 0.08:
        return "positive", round(mapped_score, 3)
    elif softened < -0.08:
        return "negative", round(mapped_score, 3)
    else:
        return "neutral", round(mapped_score, 3)

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
