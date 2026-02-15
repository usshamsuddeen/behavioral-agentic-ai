"""
Language Detection Service
Lightweight implementation using langdetect library
"""

from typing import Dict

# Language code to name and flag mapping
LANGUAGE_MAP = {
    "en": {"name": "English", "flag": "🇺🇸"},
    "es": {"name": "Spanish", "flag": "🇪🇸"},
    "fr": {"name": "French", "flag": "🇫🇷"},
    "de": {"name": "German", "flag": "🇩🇪"},
    "zh-cn": {"name": "Chinese", "flag": "🇨🇳"},
    "zh-tw": {"name": "Chinese", "flag": "🇹🇼"},
    "ar": {"name": "Arabic", "flag": "🇸🇦"},
    "ur": {"name": "Urdu", "flag": "🇵🇰"},
    "hi": {"name": "Hindi", "flag": "🇮🇳"},
    "pt": {"name": "Portuguese", "flag": "🇧🇷"},
    "ru": {"name": "Russian", "flag": "🇷🇺"},
    "ja": {"name": "Japanese", "flag": "🇯🇵"},
    "ko": {"name": "Korean", "flag": "🇰🇷"},
    "it": {"name": "Italian", "flag": "🇮🇹"},
    "nl": {"name": "Dutch", "flag": "🇳🇱"},
    "tr": {"name": "Turkish", "flag": "🇹🇷"},
    "pl": {"name": "Polish", "flag": "🇵🇱"},
    "vi": {"name": "Vietnamese", "flag": "🇻🇳"},
    "th": {"name": "Thai", "flag": "🇹🇭"},
    "id": {"name": "Indonesian", "flag": "🇮🇩"},
}


def detect_language(text: str) -> Dict:
    """
    Detect language of given text.
    Uses langdetect library with fallback to simple heuristics.
    """
    try:
        from langdetect import detect, detect_langs
        
        # Get primary language
        lang_code = detect(text)
        
        # Get confidence from probability
        lang_probs = detect_langs(text)
        confidence = lang_probs[0].prob if lang_probs else 0.8
        
        # Map to our format
        lang_info = LANGUAGE_MAP.get(lang_code, {"name": "Unknown", "flag": "🌐"})
        
        return {
            "code": lang_code,
            "name": lang_info["name"],
            "flag": lang_info["flag"],
            "confidence": round(confidence, 3)
        }
    except Exception:
        # Fallback: simple heuristic detection
        return detect_language_heuristic(text)


def detect_language_heuristic(text: str) -> Dict:
    """
    Simple heuristic-based language detection.
    Used as fallback when langdetect is not available.
    """
    text_lower = text.lower()
    
    # Spanish indicators
    spanish_words = ["hola", "gracias", "por favor", "necesito", "ayuda", "pedido", "el", "la", "los", "las"]
    if any(word in text_lower for word in spanish_words):
        return {"code": "es", "name": "Spanish", "flag": "🇪🇸", "confidence": 0.75}
    
    # French indicators
    french_words = ["bonjour", "merci", "s'il vous", "je", "nous", "vous", "avec", "pour"]
    if any(word in text_lower for word in french_words):
        return {"code": "fr", "name": "French", "flag": "🇫🇷", "confidence": 0.75}
    
    # German indicators
    german_words = ["danke", "bitte", "ich", "wir", "sie", "haben", "nicht", "sehr"]
    if any(word in text_lower for word in german_words):
        return {"code": "de", "name": "German", "flag": "🇩🇪", "confidence": 0.75}
    
    # Arabic indicators (characters)
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return {"code": "ar", "name": "Arabic", "flag": "🇸🇦", "confidence": 0.85}
    
    # Chinese indicators (characters)
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return {"code": "zh-cn", "name": "Chinese", "flag": "🇨🇳", "confidence": 0.85}
    
    # Urdu indicators (characters similar to Arabic with distinct usage)
    urdu_words = ["کا", "ہے", "میں", "اور", "کی", "سے"]
    if any(word in text for word in urdu_words):
        return {"code": "ur", "name": "Urdu", "flag": "🇵🇰", "confidence": 0.75}
    
    # Default to English
    return {"code": "en", "name": "English", "flag": "🇺🇸", "confidence": 0.7}
