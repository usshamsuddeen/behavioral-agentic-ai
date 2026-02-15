"""
Response Generator Service
Suggests contextual responses based on sentiment and conversation state

Features:
- Template-based response suggestions
- Sentiment-aware response tone
- Multi-language support
- De-escalation phrases

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
import random
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates suggested responses based on sentiment and context.
    
    Uses template-based approach with sentiment-aware selection.
    Ready for LLM integration in future versions.
    """
    
    # Response templates by sentiment and language
    TEMPLATES = {
        "en": {
            "positive": {
                "greeting": [
                    "Thank you for your kind words! 😊",
                    "We're so glad to hear that!",
                    "That's wonderful to hear! Thank you for sharing."
                ],
                "acknowledgment": [
                    "Thank you for your positive feedback!",
                    "We really appreciate your support.",
                    "It's great to know we could help!"
                ],
                "closing": [
                    "Is there anything else I can help you with today?",
                    "Let me know if you need any further assistance!",
                    "We're always here if you need us."
                ]
            },
            "neutral": {
                "greeting": [
                    "Hello! How can I assist you today?",
                    "Hi there! I'm here to help.",
                    "Welcome! What can I do for you?"
                ],
                "acknowledgment": [
                    "I understand. Let me help you with that.",
                    "Thank you for reaching out.",
                    "I'd be happy to assist you with this."
                ],
                "closing": [
                    "Is there anything else you need help with?",
                    "Feel free to reach out if you have more questions.",
                    "Don't hesitate to contact us again."
                ]
            },
            "negative": {
                "empathy": [
                    "I completely understand your frustration, and I'm sorry for any inconvenience caused.",
                    "I apologize for the experience you've had. Let me help make this right.",
                    "I'm truly sorry to hear about this issue. Your concerns are valid."
                ],
                "de_escalation": [
                    "I want to assure you that I'm personally committed to resolving this for you.",
                    "This isn't the experience we want for our customers. Let me fix this right away.",
                    "I understand this is frustrating. Let's work together to find a solution."
                ],
                "resolution": [
                    "Here's what I can do for you immediately...",
                    "Let me take care of this right now.",
                    "I'm going to prioritize your case and ensure it's resolved quickly."
                ],
                "closing": [
                    "I truly appreciate your patience while we resolve this.",
                    "Thank you for giving us the opportunity to make this right.",
                    "Please let me know if there's anything else I can do."
                ]
            },
            "urgent": {
                "acknowledgment": [
                    "I understand this is urgent and I'm treating it as a top priority.",
                    "This has been escalated to our priority queue.",
                    "I'm personally handling this to ensure a quick resolution."
                ],
                "action": [
                    "I'm taking immediate action on this.",
                    "Let me connect you with our specialist team right away.",
                    "I'm expediting this request as we speak."
                ]
            }
        },
        "es": {
            "positive": {
                "greeting": [
                    "¡Gracias por sus amables palabras! 😊",
                    "¡Nos alegra mucho escuchar eso!",
                    "¡Qué maravilloso escuchar eso!"
                ],
                "acknowledgment": [
                    "¡Gracias por su comentario positivo!",
                    "Realmente apreciamos su apoyo.",
                    "¡Es genial saber que pudimos ayudar!"
                ]
            },
            "negative": {
                "empathy": [
                    "Entiendo completamente su frustración y lamento cualquier inconveniente.",
                    "Me disculpo por la experiencia que ha tenido. Permítame ayudar.",
                    "Lamento mucho escuchar sobre este problema."
                ],
                "de_escalation": [
                    "Quiero asegurarle que estoy personalmente comprometido a resolver esto.",
                    "Esta no es la experiencia que queremos para nuestros clientes.",
                    "Entiendo que esto es frustrante. Trabajemos juntos para encontrar una solución."
                ]
            }
        },
        "fr": {
            "positive": {
                "greeting": [
                    "Merci pour vos aimables paroles ! 😊",
                    "Nous sommes très heureux d'entendre cela !",
                    "C'est merveilleux à entendre !"
                ]
            },
            "negative": {
                "empathy": [
                    "Je comprends parfaitement votre frustration et je suis désolé pour tout inconvénient.",
                    "Je m'excuse pour l'expérience que vous avez eue. Laissez-moi vous aider.",
                    "Je suis vraiment désolé d'apprendre ce problème."
                ]
            }
        }
    }
    
    def __init__(self):
        logger.info("💬 Response Generator initialized")
    
    def suggest_response(
        self,
        sentiment: str,
        response_type: str = "acknowledgment",
        language: str = "en",
        is_urgent: bool = False,
        custom_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a suggested response based on sentiment and context.
        
        Args:
            sentiment: Current sentiment (positive/neutral/negative)
            response_type: Type of response (greeting/acknowledgment/closing/empathy/etc.)
            language: Language code
            is_urgent: Whether the situation is urgent
            custom_context: Additional context for personalization
            
        Returns:
            Dict with suggested responses and metadata
        """
        # Get language templates (fallback to English)
        lang_templates = self.TEMPLATES.get(language, self.TEMPLATES["en"])
        
        # Handle urgent cases
        if is_urgent and sentiment == "negative":
            urgent_templates = lang_templates.get("urgent", {})
            response_type = "acknowledgment" if response_type == "greeting" else response_type
            if response_type in urgent_templates:
                templates = urgent_templates[response_type]
            else:
                templates = lang_templates.get("negative", {}).get("empathy", [])
        else:
            sentiment_templates = lang_templates.get(sentiment, lang_templates.get("neutral", {}))
            templates = sentiment_templates.get(response_type, [])
        
        if not templates:
            # Fallback
            templates = ["How can I help you today?"]
        
        # Select responses
        primary_response = random.choice(templates)
        alternatives = [t for t in templates if t != primary_response][:2]
        
        return {
            "suggested_response": primary_response,
            "alternatives": alternatives,
            "tone": self._get_tone_guidance(sentiment, is_urgent),
            "keywords_to_use": self._get_recommended_keywords(sentiment),
            "keywords_to_avoid": self._get_keywords_to_avoid(sentiment),
            "language": language,
            "sentiment_context": sentiment
        }
    
    def generate_de_escalation_sequence(
        self,
        language: str = "en"
    ) -> List[Dict[str, str]]:
        """
        Generate a sequence of de-escalation responses.
        
        Returns:
            List of response steps for de-escalation
        """
        lang_templates = self.TEMPLATES.get(language, self.TEMPLATES["en"])
        negative_templates = lang_templates.get("negative", {})
        
        sequence = []
        
        # Step 1: Empathy
        if "empathy" in negative_templates:
            sequence.append({
                "step": 1,
                "type": "empathy",
                "response": random.choice(negative_templates["empathy"]),
                "purpose": "Acknowledge the customer's feelings"
            })
        
        # Step 2: De-escalation
        if "de_escalation" in negative_templates:
            sequence.append({
                "step": 2,
                "type": "de_escalation",
                "response": random.choice(negative_templates["de_escalation"]),
                "purpose": "Take ownership and commit to resolution"
            })
        
        # Step 3: Resolution
        if "resolution" in negative_templates:
            sequence.append({
                "step": 3,
                "type": "resolution",
                "response": random.choice(negative_templates["resolution"]),
                "purpose": "Provide concrete action"
            })
        
        # Step 4: Closing
        if "closing" in negative_templates:
            sequence.append({
                "step": 4,
                "type": "closing",
                "response": random.choice(negative_templates["closing"]),
                "purpose": "Express gratitude and offer continued support"
            })
        
        return sequence
    
    def _get_tone_guidance(self, sentiment: str, is_urgent: bool) -> str:
        """Get guidance on response tone."""
        if is_urgent:
            return "Immediate, decisive, and reassuring. Show urgency in resolution."
        elif sentiment == "negative":
            return "Empathetic, apologetic, and solution-focused. Avoid defensive language."
        elif sentiment == "positive":
            return "Warm, appreciative, and enthusiastic. Match their positive energy."
        else:
            return "Professional, helpful, and clear. Focus on resolution."
    
    def _get_recommended_keywords(self, sentiment: str) -> List[str]:
        """Get keywords to use based on sentiment."""
        keywords = {
            "negative": ["understand", "apologize", "resolve", "priority", "immediately", "personally"],
            "positive": ["thank you", "great", "appreciate", "wonderful", "glad"],
            "neutral": ["help", "assist", "happy to", "let me", "certainly"]
        }
        return keywords.get(sentiment, keywords["neutral"])
    
    def _get_keywords_to_avoid(self, sentiment: str) -> List[str]:
        """Get keywords to avoid based on sentiment."""
        avoid = {
            "negative": ["unfortunately", "policy", "can't", "won't", "but"],
            "positive": ["issue", "problem", "sorry"],
            "neutral": []
        }
        return avoid.get(sentiment, [])


# Global response generator instance (singleton)
_generator = None


def get_response_generator() -> ResponseGenerator:
    """Get the global response generator instance."""
    global _generator
    if _generator is None:
        _generator = ResponseGenerator()
    return _generator
