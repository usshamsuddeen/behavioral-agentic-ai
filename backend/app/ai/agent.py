"""
AI Agent Orchestrator for Behavioral Agentic AI
Main agent that coordinates all AI components for intelligent responses

Features:
- RAG-based response generation
- Sentiment-aware response adaptation
- Escalation detection integration
- Conversation context management
- Multi-step reasoning

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from app.ai.retrieval import get_retrieval_service
from app.ai.llm import get_llm_service, LLMResponse
from app.services.sentiment import analyze_sentiment
from app.services.escalation import check_escalation_triggers, calculate_escalation_priority

# Configure logging
logger = logging.getLogger(__name__)


class AgentAction(Enum):
    """Possible agent actions."""
    RESPOND = "respond"           # Generate AI response
    ESCALATE = "escalate"         # Escalate to human
    REQUEST_INFO = "request_info" # Ask for clarification
    TRANSFER = "transfer"         # Transfer to specialist


@dataclass
class AgentContext:
    """Context for agent processing."""
    client_id: str
    conversation_id: str
    user_message: str
    conversation_history: List[Dict] = field(default_factory=list)
    company_name: str = "Our Company"
    company_guidelines: Optional[str] = None
    support_email: Optional[str] = None
    current_frustration: float = 0.0
    detected_language: str = "en"  # ISO code from language detection
    pre_sentiment: Optional[Dict] = None  # Reuse sentiment from widget_api


@dataclass
class AgentResult:
    """Result of agent processing."""
    action: AgentAction
    response: str
    sentiment: Dict
    escalation: Dict
    context_used: List[str]
    confidence: float
    requires_human: bool
    metadata: Dict = field(default_factory=dict)


class AIAgent:
    """
    Intelligent AI Agent for customer support.
    
    Orchestrates sentiment analysis, knowledge retrieval,
    response generation, and escalation handling.
    
    Attributes:
        retrieval: RAG retrieval service
        llm: LLM generation service
        escalation_threshold: Confidence below which to escalate
    """
    
    def __init__(
        self,
        escalation_threshold: float = 0.5,
        max_auto_response_frustration: float = 0.7
    ):
        """
        Initialize AI Agent.
        
        Args:
            escalation_threshold: Confidence below which to recommend escalation
            max_auto_response_frustration: Max frustration level for auto-response
        """
        self.retrieval = get_retrieval_service()
        self.llm = get_llm_service()
        self.escalation_threshold = escalation_threshold
        self.max_auto_response_frustration = max_auto_response_frustration
    
    def process_message(self, context: AgentContext) -> AgentResult:
        """
        Process a customer message and generate appropriate response.
        
        Args:
            context: AgentContext with all required information
            
        Returns:
            AgentResult with action, response, and metadata
        """
        logger.info(f"🤖 Processing message for client: {context.client_id}")
        
        # Step 1: Reuse pre-computed sentiment if available, else analyze
        if context.pre_sentiment:
            sentiment_result = context.pre_sentiment
        else:
            sentiment_result = self._analyze_sentiment(context.user_message)
        
        # Step 2: Check for escalation triggers
        escalation_result = self._check_escalation(
            message=context.user_message,
            sentiment=sentiment_result,
            frustration=context.current_frustration
        )
        
        # Step 3: Decide if we should escalate immediately
        if self._should_escalate_immediately(escalation_result, sentiment_result):
            return self._create_escalation_result(
                sentiment=sentiment_result,
                escalation=escalation_result,
                reason="High frustration or critical trigger detected"
            )
        
        # Step 4: Retrieve relevant context from knowledge base
        context_docs, raw_results = self._retrieve_context(
            client_id=context.client_id,
            query=context.user_message,
            conversation_history=context.conversation_history
        )
        
        # Step 5: Generate response using LLM
        llm_response = self._generate_response(
            context=context,
            context_docs=context_docs,
            sentiment=sentiment_result
        )
        
        # Step 6: Evaluate response and decide action
        action, requires_human = self._evaluate_response(
            llm_response=llm_response,
            sentiment=sentiment_result,
            escalation=escalation_result
        )
        
        # Step 7: Post-process response if needed
        final_response = self._post_process_response(
            response=llm_response.response,
            action=action,
            sentiment=sentiment_result
        )
        
        return AgentResult(
            action=action,
            response=final_response,
            sentiment=sentiment_result,
            escalation=escalation_result,
            context_used=[r.text[:200] for r in raw_results[:3]] if raw_results else [],
            confidence=llm_response.confidence,
            requires_human=requires_human,
            metadata={
                "llm_model": llm_response.model,
                "tokens_used": llm_response.tokens_used,
                "retrieval_count": len(raw_results) if raw_results else 0,
                "llm_success": llm_response.success
            }
        )
    
    def _analyze_sentiment(self, message: str) -> Dict:
        """Analyze message sentiment."""
        try:
            result = analyze_sentiment(message)
            return {
                "sentiment": result.get("sentiment", "neutral"),
                "score": result.get("score", 0.5),
                "confidence": result.get("confidence", 0.5),
                "label": result.get("label", "neutral"),
                "is_urgent": result.get("is_urgent", False)
            }
        except Exception as e:
            logger.error(f"❌ Sentiment analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "confidence": 0.0,
                "label": "neutral",
                "is_urgent": False
            }
    
    def _check_escalation(
        self,
        message: str,
        sentiment: Dict,
        frustration: float
    ) -> Dict:
        """Check for escalation triggers."""
        try:
            triggers = check_escalation_triggers(message, frustration)
            priority = calculate_escalation_priority(
                sentiment_score=sentiment.get("score", 0.5),
                frustration_level=frustration,
                message_count=1,
                has_triggers=triggers.get("should_escalate", False)
            )
            
            return {
                "should_escalate": triggers.get("should_escalate", False),
                "triggers": triggers.get("keywords", []),
                "priority": priority if isinstance(priority, str) else "normal",
                "priority_score": triggers.get("trigger_score", 0.5),
                "reason": triggers.get("reason", "")
            }
        except Exception as e:
            logger.error(f"[ERROR] Escalation check failed: {e}")
            return {
                "should_escalate": False,
                "triggers": [],
                "priority": "normal",
                "priority_score": 0.5,
                "reason": ""
            }
    
    def _should_escalate_immediately(self, escalation: Dict, sentiment: Dict) -> bool:
        """Determine if immediate escalation is needed.
        
        IMPORTANT: BERT sentiment returns -1.0 for ALL negative messages,
        even innocuous ones like "Can I cancel my order?". Therefore we
        CANNOT use sentiment score alone as an escalation trigger.
        We require keyword/trigger evidence alongside sentiment.
        """
        # Very high trigger score from keywords/frustration
        if escalation.get("trigger_score", 0.0) >= 0.85:
            return True

        # Legal or media threats found in matched keywords
        critical_triggers = ["legal", "lawsuit", "lawyer", "media", "attorney", "sue"]
        matched_keywords = escalation.get("keywords", []) or escalation.get("triggers", [])
        for kw in matched_keywords:
            if any(ct in kw.lower() for ct in critical_triggers):
                return True

        # Negative sentiment + significant keyword evidence (combined signal)
        # V5 FIX: Raised thresholds — prevents escalation on normal queries
        # that happen to contain words like "cancel" or "problem".
        if sentiment.get("score", 0.5) < 0.20 and escalation.get("trigger_score", 0.0) >= 0.50:
            return True

        return False
    
    def _retrieve_context(
        self,
        client_id: str,
        query: str,
        conversation_history: list = None
    ) -> tuple:
        """
        Retrieve relevant knowledge base context.
        
        For short conversational replies (yes, ok, sure, etc.), uses the
        PREVIOUS user message as the search query so RAG context stays
        consistent and the system prompt doesn't flip to no-context mode.
        """
        try:
            effective_query = query
            
            # Detect short/conversational messages that won't match anything in RAG
            SHORT_REPLIES = {
                "yes", "yeah", "yep", "yea", "sure", "ok", "okay", "please",
                "no", "nope", "nah", "thanks", "thank you", "ty", "thx",
                "go ahead", "do it", "proceed", "confirm", "alright", "fine",
                "great", "cool", "nice", "perfect", "awesome", "good",
                "hmm", "hm", "ah", "oh", "wow",
            }
            query_clean = query.lower().strip(" .,!?")
            
            if query_clean in SHORT_REPLIES or len(query_clean) <= 4:
                # Find the last substantive user message from history
                if conversation_history:
                    for msg in reversed(conversation_history):
                        if msg.get("role") == "user":
                            prev = msg.get("content", "").strip()
                            prev_clean = prev.lower().strip(" .,!?")
                            if prev_clean not in SHORT_REPLIES and len(prev_clean) > 4:
                                effective_query = prev
                                logger.info(f"🔄 Short reply '{query}' → re-using previous query: '{effective_query[:50]}'")
                                break
            
            # Detect "show ALL products" queries — need more results
            PRODUCT_LIST_SIGNALS = [
                "all product", "show product", "list product", "your product",
                "what product", "show me product", "menu", "catalog", "catalogue",
                "what do you sell", "what do you have", "what do you offer",
                "show everything", "all items", "list everything",
            ]
            is_product_listing = any(sig in effective_query.lower() for sig in PRODUCT_LIST_SIGNALS)
            top_k = 20 if is_product_listing else 5
            max_tokens = 4000 if is_product_listing else 2000
            
            context_str, results = self.retrieval.retrieve_context(
                client_id=client_id,
                query=effective_query,
                max_tokens=max_tokens,
                top_k=top_k
            )
            
            # Convert to list of document strings
            docs = [context_str] if context_str else []
            
            return docs, results
            
        except Exception as e:
            logger.error(f"❌ Context retrieval failed: {e}")
            return [], []
    
    def _generate_response(
        self,
        context: AgentContext,
        context_docs: List[str],
        sentiment: Dict
    ) -> LLMResponse:
        """Generate LLM response with debug logging."""
        logger.info(f"🔄 Generating LLM response — docs: {len(context_docs)}, sentiment: {sentiment.get('sentiment', 'unknown')}")

        result = self.llm.generate_response(
            user_message=context.user_message,
            context_documents=context_docs,
            company_name=context.company_name,
            conversation_history=context.conversation_history,
            guidelines=context.company_guidelines,
            support_email=context.support_email,
            sentiment=sentiment.get("sentiment"),
            is_urgent=sentiment.get("is_urgent", False),
            language=context.detected_language
        )

        logger.info(
            f"📝 LLM result — model: {result.model}, success: {result.success}, "
            f"confidence: {result.confidence:.2f}, tokens: {result.tokens_used}"
        )
        if not result.success:
            logger.warning(f"⚠️ LLM non-success — error: {result.error}, response preview: {result.response[:100]}")

        return result
    
    def _evaluate_response(
        self,
        llm_response: LLMResponse,
        sentiment: Dict,
        escalation: Dict
    ) -> tuple:
        """Evaluate response quality and determine action."""

        # Default action is to respond
        action = AgentAction.RESPOND
        requires_human = False

        # Low confidence + extremely negative sentiment — suggest human review
        # V5 FIX: Raised thresholds to prevent false flags when KB is empty.
        # Empty KB → fallback responses have 0.4 confidence, which previously
        # triggered requires_human on any mildly negative message.
        if llm_response.confidence < 0.2 and sentiment.get("score", 0.5) < 0.20:
            requires_human = True

        # LLM truly failed (not just using fallback template) — flag for review
        if not llm_response.success and llm_response.confidence < 0.1:
            action = AgentAction.ESCALATE
            requires_human = True

        # Escalation triggered by escalation checker
        if escalation.get("should_escalate"):
            action = AgentAction.ESCALATE
            requires_human = True

        # Extremely negative sentiment with low confidence
        if sentiment.get("score", 0.5) < 0.15 and llm_response.confidence < 0.3:
            requires_human = True

        return action, requires_human
    
    def _post_process_response(
        self,
        response: str,
        action: AgentAction,
        sentiment: Dict
    ) -> str:
        """Post-process response for final output."""
        
        # Clean up response
        response = response.strip()
        
        # Add empathy prefix for negative sentiment
        if sentiment.get("sentiment") == "negative" and not response.lower().startswith(("i understand", "i'm sorry", "i apologize")):
            empathy_phrases = [
                "I understand your frustration. ",
                "I'm sorry to hear about this issue. ",
                "I appreciate you bringing this to our attention. "
            ]
            import random
            response = random.choice(empathy_phrases) + response
        
        # Add escalation notice if needed
        if action == AgentAction.ESCALATE:
            if "connect" not in response.lower() and "team member" not in response.lower():
                response += "\n\nI'm also notifying our team so someone can follow up with you directly."
        
        return response
    
    def _create_escalation_result(
        self,
        sentiment: Dict,
        escalation: Dict,
        reason: str
    ) -> AgentResult:
        """Create an immediate escalation result."""
        
        responses = {
            "urgent": "I can see this is urgent and important. I'm immediately connecting you with a senior team member who can help resolve this right away.",
            "high": "I understand this is a priority issue. Let me connect you with a specialist who can provide immediate assistance.",
            "default": "I want to make sure you get the best possible help. I'm connecting you with a team member who specializes in this area."
        }
        
        priority = escalation.get("priority", "default")
        response = responses.get(priority, responses["default"])
        
        return AgentResult(
            action=AgentAction.ESCALATE,
            response=response,
            sentiment=sentiment,
            escalation=escalation,
            context_used=[],
            confidence=0.0,
            requires_human=True,
            metadata={
                "escalation_reason": reason,
                "auto_escalated": True
            }
        )
    
    def get_agent_info(self) -> Dict:
        """Get agent configuration information."""
        return {
            "escalation_threshold": self.escalation_threshold,
            "max_auto_response_frustration": self.max_auto_response_frustration,
            "llm_available": self.llm.is_available(),
            "llm_model": self.llm.model
        }


# Singleton instance
_agent: Optional[AIAgent] = None


def get_ai_agent() -> AIAgent:
    """
    Get the global AI agent instance.
    
    Returns:
        AIAgent instance
    """
    global _agent
    
    if _agent is None:
        _agent = AIAgent()
    
    return _agent
