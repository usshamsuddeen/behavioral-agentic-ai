"""
Service Layer Tests
Tests for sentiment, prediction, and response generation services
"""

import pytest


class TestSentimentService:
    """Test sentiment analysis service"""
    
    def test_analyze_positive_sentiment(self):
        """Test positive sentiment detection"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("I love this product! It's amazing!", "en")
        
        assert result["sentiment"] == "positive"
        assert result["score"] > 0.5
        assert "label" in result
        assert "emoji" in result
    
    def test_analyze_negative_sentiment(self):
        """Test negative sentiment detection"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("This is terrible! I hate it!", "en")
        
        assert result["sentiment"] == "negative"
        assert "is_urgent" in result
    
    def test_analyze_neutral_sentiment(self):
        """Test neutral sentiment detection"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("The product arrived today.", "en")
        
        assert result["sentiment"] in ["neutral", "positive"]
    
    def test_detect_urgency(self):
        """Test urgent keyword detection"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("I will call my lawyer if this isn't fixed!", "en")
        
        assert result["is_urgent"] == True
    
    def test_detect_shouting(self):
        """Test caps lock (shouting) detection"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("THIS IS UNACCEPTABLE!!!", "en")
        
        assert result["is_shouting"] == True
    
    def test_multilingual_spanish(self):
        """Test Spanish sentiment analysis"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("Estoy muy feliz con el servicio", "es")
        
        assert result["sentiment"] == "positive"
    
    def test_multilingual_french(self):
        """Test French sentiment analysis"""
        from app.services.sentiment import analyze_sentiment
        
        result = analyze_sentiment("C'est terrible, je suis fâché", "fr")
        
        assert result["sentiment"] == "negative"


class TestLanguageService:
    """Test language detection service"""
    
    def test_detect_english(self):
        """Test English language detection"""
        from app.services.language import detect_language
        
        result = detect_language("Hello, how are you today?")
        
        assert result["language"].startswith("en")
    
    def test_detect_spanish(self):
        """Test Spanish language detection"""
        from app.services.language import detect_language
        
        result = detect_language("Hola, ¿cómo estás hoy?")
        
        assert result["language"] == "es"
    
    def test_detect_french(self):
        """Test French language detection"""
        from app.services.language import detect_language
        
        result = detect_language("Bonjour, comment allez-vous?")
        
        assert result["language"] == "fr"


class TestEscalationService:
    """Test escalation detection service"""
    
    def test_detect_escalation_trigger(self):
        """Test escalation trigger detection"""
        from app.services.escalation import check_escalation_triggers
        
        result = check_escalation_triggers("I want to speak to your manager!")
        
        assert result["should_escalate"] == True
        assert len(result["matched_keywords"]) > 0
    
    def test_no_escalation_needed(self):
        """Test normal message without escalation"""
        from app.services.escalation import check_escalation_triggers
        
        result = check_escalation_triggers("Thank you for your help")
        
        assert result["should_escalate"] == False
    
    def test_legal_threat_detection(self):
        """Test legal threat detection"""
        from app.services.escalation import check_escalation_triggers
        
        result = check_escalation_triggers("I will sue you and contact my attorney!")
        
        assert result["should_escalate"] == True
        assert "lawyer" in result["matched_keywords"] or "sue" in result["matched_keywords"] or "attorney" in result["matched_keywords"]


class TestPredictionService:
    """Test behavioral prediction service"""
    
    def test_churn_risk_calculation(self):
        """Test churn risk calculation"""
        from app.services.prediction import get_predictor
        
        predictor = get_predictor()
        result = predictor.calculate_churn_risk(
            sentiment_history=[
                {"sentiment": "negative"},
                {"sentiment": "negative"},
                {"sentiment": "negative"}
            ],
            escalation_count=2,
            resolution_time_hours=48
        )
        
        assert "churn_risk_score" in result
        assert "risk_level" in result
        assert result["risk_level"] in ["low", "medium", "high", "critical"]
    
    def test_escalation_probability(self):
        """Test escalation probability prediction"""
        from app.services.prediction import get_predictor
        
        predictor = get_predictor()
        result = predictor.predict_escalation_probability(
            current_sentiment="negative",
            sentiment_score=0.9,
            message_count=8,
            has_urgent_keywords=True,
            is_shouting=True
        )
        
        assert "escalation_probability" in result
        assert result["escalation_probability"] > 0.5
        assert result["will_escalate"] == True
    
    def test_resolution_time_estimate(self):
        """Test resolution time estimation"""
        from app.services.prediction import get_predictor
        
        predictor = get_predictor()
        result = predictor.estimate_resolution_time(
            issue_category="refund",
            sentiment="negative"
        )
        
        assert "estimated_hours" in result
        assert result["estimated_hours"] > 0


class TestResponseGenerator:
    """Test response generation service"""
    
    def test_generate_positive_response(self):
        """Test positive response generation"""
        from app.services.response_generator import get_response_generator
        
        generator = get_response_generator()
        result = generator.suggest_response(
            sentiment="positive",
            response_type="acknowledgment"
        )
        
        assert "suggested_response" in result
        assert len(result["suggested_response"]) > 0
    
    def test_generate_negative_response(self):
        """Test negative sentiment response"""
        from app.services.response_generator import get_response_generator
        
        generator = get_response_generator()
        result = generator.suggest_response(
            sentiment="negative",
            response_type="empathy"
        )
        
        assert "suggested_response" in result
        assert "tone" in result
    
    def test_de_escalation_sequence(self):
        """Test de-escalation sequence generation"""
        from app.services.response_generator import get_response_generator
        
        generator = get_response_generator()
        result = generator.generate_de_escalation_sequence("en")
        
        assert len(result) >= 3
        assert result[0]["type"] == "empathy"
    
    def test_multilingual_response(self):
        """Test Spanish response generation"""
        from app.services.response_generator import get_response_generator
        
        generator = get_response_generator()
        result = generator.suggest_response(
            sentiment="positive",
            language="es"
        )
        
        assert "suggested_response" in result
