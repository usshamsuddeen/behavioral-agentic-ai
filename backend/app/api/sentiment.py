"""
Sentiment API - Sentiment and language analysis endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.sentiment import analyze_sentiment
from app.services.language import detect_language

router = APIRouter()


class SentimentRequest(BaseModel):
    """Request body for sentiment analysis"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = None


class LanguageRequest(BaseModel):
    """Request body for language detection"""
    text: str = Field(..., min_length=1, max_length=5000)


@router.post("/analyze/sentiment")
async def analyze_text_sentiment(request: SentimentRequest):
    """
    Analyze sentiment of given text.
    Returns sentiment (positive/neutral/negative), score, and label.
    """
    result = analyze_sentiment(request.text)
    
    return {
        "text": request.text[:100] + "..." if len(request.text) > 100 else request.text,
        "sentiment": result["sentiment"],
        "score": result["score"],
        "label": result["label"],
        "emoji": result["emoji"],
        "confidence": result["confidence"]
    }


@router.post("/analyze/language")
async def detect_text_language(request: LanguageRequest):
    """
    Detect language of given text.
    Returns language code, name, and flag emoji.
    """
    result = detect_language(request.text)
    
    return {
        "text": request.text[:100] + "..." if len(request.text) > 100 else request.text,
        "language_code": result["code"],
        "language_name": result["name"],
        "language_flag": result["flag"],
        "confidence": result["confidence"]
    }


@router.post("/analyze/full")
async def full_analysis(request: SentimentRequest):
    """
    Perform full analysis: sentiment + language detection.
    """
    sentiment_result = analyze_sentiment(request.text)
    language_result = detect_language(request.text)
    
    return {
        "text": request.text[:100] + "..." if len(request.text) > 100 else request.text,
        "sentiment": {
            "sentiment": sentiment_result["sentiment"],
            "score": sentiment_result["score"],
            "label": sentiment_result["label"],
            "emoji": sentiment_result["emoji"],
            "confidence": sentiment_result["confidence"]
        },
        "language": {
            "code": language_result["code"],
            "name": language_result["name"],
            "flag": language_result["flag"],
            "confidence": language_result["confidence"]
        }
    }
