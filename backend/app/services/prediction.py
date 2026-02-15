"""
Behavioral Prediction Service
Predicts customer behavior based on sentiment history and conversation patterns

Features:
- Churn risk scoring
- Escalation probability prediction
- Resolution time estimation
- Customer satisfaction prediction

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class BehavioralPredictor:
    """
    Predicts customer behavior based on conversation history and sentiment patterns.
    
    Uses rule-based scoring with configurable thresholds.
    Ready for ML model integration in future versions.
    """
    
    # Churn risk thresholds
    CHURN_THRESHOLDS = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.8
    }
    
    # Sentiment score weights
    SENTIMENT_WEIGHTS = {
        "negative": -1.0,
        "neutral": 0.0,
        "positive": 0.5
    }
    
    def __init__(self):
        logger.info("🧠 Behavioral Predictor initialized")
    
    def calculate_churn_risk(
        self,
        sentiment_history: List[Dict],
        escalation_count: int = 0,
        resolution_time_hours: float = 0,
        repeat_contact_count: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate customer churn risk based on behavioral signals.
        
        Args:
            sentiment_history: List of sentiment analysis results
            escalation_count: Number of escalations
            resolution_time_hours: Average resolution time
            repeat_contact_count: Number of repeat contacts
            
        Returns:
            Dict with churn risk score and factors
        """
        risk_score = 0.0
        factors = []
        
        # Factor 1: Sentiment trend (30% weight)
        if sentiment_history:
            negative_count = sum(1 for s in sentiment_history if s.get("sentiment") == "negative")
            negative_ratio = negative_count / len(sentiment_history)
            
            sentiment_contribution = negative_ratio * 0.3
            risk_score += sentiment_contribution
            
            if negative_ratio > 0.5:
                factors.append({
                    "factor": "High negative sentiment",
                    "impact": "high",
                    "value": f"{negative_ratio:.0%} negative messages"
                })
        
        # Factor 2: Escalation frequency (25% weight)
        if escalation_count > 0:
            escalation_contribution = min(escalation_count * 0.08, 0.25)
            risk_score += escalation_contribution
            
            if escalation_count >= 2:
                factors.append({
                    "factor": "Multiple escalations",
                    "impact": "high",
                    "value": f"{escalation_count} escalations"
                })
        
        # Factor 3: Resolution time (20% weight)
        if resolution_time_hours > 24:
            time_contribution = min((resolution_time_hours - 24) * 0.005, 0.2)
            risk_score += time_contribution
            
            factors.append({
                "factor": "Long resolution time",
                "impact": "medium",
                "value": f"{resolution_time_hours:.1f} hours"
            })
        
        # Factor 4: Repeat contacts (25% weight)
        if repeat_contact_count > 2:
            repeat_contribution = min((repeat_contact_count - 2) * 0.05, 0.25)
            risk_score += repeat_contribution
            
            factors.append({
                "factor": "Repeat contacts",
                "impact": "medium",
                "value": f"{repeat_contact_count} contacts"
            })
        
        # Determine risk level
        if risk_score >= self.CHURN_THRESHOLDS["high"]:
            risk_level = "critical"
        elif risk_score >= self.CHURN_THRESHOLDS["medium"]:
            risk_level = "high"
        elif risk_score >= self.CHURN_THRESHOLDS["low"]:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "churn_risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "factors": factors,
            "recommendation": self._get_churn_recommendation(risk_level)
        }
    
    def predict_escalation_probability(
        self,
        current_sentiment: str,
        sentiment_score: float,
        message_count: int,
        has_urgent_keywords: bool,
        is_shouting: bool
    ) -> Dict[str, Any]:
        """
        Predict probability of escalation based on current conversation state.
        
        Args:
            current_sentiment: Current sentiment (positive/neutral/negative)
            sentiment_score: Sentiment intensity (0-1)
            message_count: Number of messages in conversation
            has_urgent_keywords: Whether urgent keywords detected
            is_shouting: Whether customer is using caps
            
        Returns:
            Dict with escalation probability and triggers
        """
        probability = 0.0
        triggers = []
        
        # Base probability from sentiment
        if current_sentiment == "negative":
            probability += 0.3 + (sentiment_score * 0.2)
            triggers.append("Negative sentiment detected")
        
        # Urgent keywords
        if has_urgent_keywords:
            probability += 0.25
            triggers.append("Urgent keywords (lawyer, refund, etc.)")
        
        # Shouting/caps
        if is_shouting:
            probability += 0.15
            triggers.append("Customer frustration (caps lock)")
        
        # Message count (more messages = more frustration)
        if message_count > 5:
            probability += min((message_count - 5) * 0.03, 0.15)
            triggers.append(f"Extended conversation ({message_count} messages)")
        
        probability = min(probability, 1.0)
        
        return {
            "escalation_probability": round(probability, 3),
            "will_escalate": probability > 0.5,
            "triggers": triggers,
            "recommendation": self._get_escalation_recommendation(probability)
        }
    
    def estimate_resolution_time(
        self,
        issue_category: str = "general",
        sentiment: str = "neutral",
        is_escalated: bool = False
    ) -> Dict[str, Any]:
        """
        Estimate time to resolution based on issue characteristics.
        
        Args:
            issue_category: Type of issue
            sentiment: Current sentiment
            is_escalated: Whether already escalated
            
        Returns:
            Dict with estimated resolution time
        """
        # Base times by category (in hours)
        base_times = {
            "refund": 4.0,
            "technical": 6.0,
            "billing": 3.0,
            "shipping": 2.0,
            "general": 1.5,
            "complaint": 8.0
        }
        
        base_time = base_times.get(issue_category, 2.0)
        
        # Adjust for sentiment
        if sentiment == "negative":
            base_time *= 1.5
        elif sentiment == "positive":
            base_time *= 0.8
        
        # Adjust for escalation
        if is_escalated:
            base_time *= 1.3
        
        return {
            "estimated_hours": round(base_time, 1),
            "estimated_range": {
                "min": round(base_time * 0.7, 1),
                "max": round(base_time * 1.5, 1)
            },
            "confidence": 0.75 if issue_category != "general" else 0.5
        }
    
    def predict_satisfaction(
        self,
        sentiment_history: List[Dict],
        resolution_achieved: bool = False,
        response_time_minutes: float = 5.0
    ) -> Dict[str, Any]:
        """
        Predict customer satisfaction score.
        
        Args:
            sentiment_history: List of sentiment results
            resolution_achieved: Whether issue was resolved
            response_time_minutes: Average response time
            
        Returns:
            Dict with predicted CSAT score
        """
        base_score = 3.0  # Neutral starting point (1-5 scale)
        
        # Sentiment trajectory
        if sentiment_history:
            recent = sentiment_history[-3:] if len(sentiment_history) >= 3 else sentiment_history
            positive_recent = sum(1 for s in recent if s.get("sentiment") == "positive")
            negative_recent = sum(1 for s in recent if s.get("sentiment") == "negative")
            
            base_score += (positive_recent - negative_recent) * 0.5
        
        # Resolution bonus
        if resolution_achieved:
            base_score += 1.0
        
        # Response time factor
        if response_time_minutes <= 2:
            base_score += 0.3
        elif response_time_minutes > 10:
            base_score -= 0.5
        
        # Clamp to 1-5 range
        predicted_csat = max(1.0, min(5.0, base_score))
        
        return {
            "predicted_csat": round(predicted_csat, 1),
            "csat_label": self._get_csat_label(predicted_csat),
            "confidence": 0.7,
            "improvement_suggestions": self._get_improvement_suggestions(predicted_csat)
        }
    
    def _get_churn_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on churn risk level."""
        recommendations = {
            "critical": "Immediate intervention required. Assign senior agent and offer compensation.",
            "high": "Priority handling needed. Consider proactive outreach and expedited resolution.",
            "medium": "Monitor closely. Ensure timely responses and follow-up.",
            "low": "Standard handling. Focus on quick resolution."
        }
        return recommendations.get(risk_level, "Continue standard process.")
    
    def _get_escalation_recommendation(self, probability: float) -> str:
        """Get recommendation based on escalation probability."""
        if probability > 0.7:
            return "Pre-emptive escalation recommended. Transfer to specialist immediately."
        elif probability > 0.5:
            return "High escalation risk. Prepare handoff package and alert supervisor."
        elif probability > 0.3:
            return "Moderate risk. Apply de-escalation techniques and empathetic responses."
        else:
            return "Low risk. Continue normal handling."
    
    def _get_csat_label(self, score: float) -> str:
        """Get label for CSAT score."""
        if score >= 4.5:
            return "Excellent"
        elif score >= 4.0:
            return "Good"
        elif score >= 3.0:
            return "Average"
        elif score >= 2.0:
            return "Poor"
        else:
            return "Critical"
    
    def _get_improvement_suggestions(self, score: float) -> List[str]:
        """Get suggestions to improve satisfaction."""
        suggestions = []
        
        if score < 4.0:
            suggestions.append("Reduce response time")
        if score < 3.5:
            suggestions.append("Offer proactive updates")
        if score < 3.0:
            suggestions.append("Consider compensation or goodwill gesture")
        if score < 2.5:
            suggestions.append("Escalate to customer success team")
        
        return suggestions if suggestions else ["Maintain current service quality"]


# Global predictor instance (singleton)
_predictor = None


def get_predictor() -> BehavioralPredictor:
    """Get the global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = BehavioralPredictor()
    return _predictor
