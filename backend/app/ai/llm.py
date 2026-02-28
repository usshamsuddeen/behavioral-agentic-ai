"""
LLM Integration for Behavioral Agentic AI
Provider-agnostic — works with any OpenAI-compatible API:
  - fal.ai          (DeepSeek, Llama, etc.)
  - OpenRouter      (Free models: Llama 3, Mistral, Gemma)
  - OpenAI          (GPT-4o, GPT-4o-mini)
  - Anthropic proxy  (Claude via OpenAI-compatible gateway)
  - Any other OpenAI-compatible endpoint

All configuration via .env — zero code changes to switch providers:
  LLM_BASE_URL   = API endpoint (e.g. https://fal.ai/api/v1)
  LLM_API_KEY    = Bearer token
  LLM_MODEL      = Model identifier
  LLM_FALLBACK_MODEL = Fallback model (optional)

Author: Behavioral Agentic AI Team
Version: 4.0.0
"""

import os
import logging
import time
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import httpx

# Configure logging
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Provider-agnostic configuration — all from .env
# ═══════════════════════════════════════════════════════════════════
DEFAULT_BASE_URL = "https://fal.ai/api/v1"  # fal.ai OpenAI-compatible endpoint
DEFAULT_MODEL = "deepseek-r1"               # DeepSeek R1 on fal.ai
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "deepseek-v3")  # Fallback model
MAX_TOKENS = 500
TEMPERATURE = 0.7


@dataclass
class LLMResponse:
    """Container for LLM response."""
    response: str
    confidence: float
    model: str
    tokens_used: int
    success: bool
    error: Optional[str] = None


class LLMService:
    """
    LLM integration service for response generation.
    
    Provides RAG-based response generation using
    OpenRouter API with free model access (Llama 3, Mistral, etc.)
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize LLM service.
        
        Provider-agnostic: reads LLM_API_KEY, LLM_BASE_URL, LLM_MODEL from .env.
        Falls back to OPENROUTER_API_KEY for backward compatibility.
        
        Args:
            model: LLM model name (overrides env)
            api_key: API key (overrides env)
            base_url: Base URL (overrides env)
        """
        # API key: LLM_API_KEY > OPENROUTER_API_KEY > constructor arg
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self.base_url = base_url or os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
        self._initialized = False
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Rate limiting
        
        # Detect provider for logging
        if "fal.ai" in self.base_url:
            self._provider = "fal.ai"
        elif "openrouter" in self.base_url:
            self._provider = "openrouter"
        elif "openai.com" in self.base_url:
            self._provider = "openai"
        elif "anthropic" in self.base_url:
            self._provider = "anthropic"
        else:
            self._provider = "custom"
        
        # ── Startup diagnostics ──
        key_preview = f"{self.api_key[:8]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 12 else "NOT SET"
        logger.info(
            f"🔑 LLM init: provider={self._provider} | model={self.model} | "
            f"url={self.base_url} | key={key_preview} | available={self.is_available()}"
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers — works with all OpenAI-compatible providers."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter-specific headers (harmlessly ignored by other providers)
        if self._provider == "openrouter":
            headers["HTTP-Referer"] = "https://behavioral-agentic-ai.local"
            headers["X-Title"] = "Behavioral Agentic AI"
        return headers
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.api_key is not None and len(self.api_key) > 10
    
    def _rate_limit(self):
        """Simple rate limiting to avoid API throttling."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def generate_response(
        self,
        user_message: str,
        context_documents: List[str],
        company_name: str = "Our Company",
        conversation_history: Optional[List[Dict]] = None,
        guidelines: Optional[str] = None,
        sentiment: Optional[str] = None,
        is_urgent: bool = False,
        language: str = "en"
    ) -> LLMResponse:
        """
        Generate a response using RAG approach.
        
        Args:
            user_message: Customer's message
            context_documents: Retrieved knowledge base documents
            company_name: Company name for personalization
            conversation_history: Previous messages
            guidelines: Company response guidelines
            sentiment: Detected sentiment
            is_urgent: Whether this is urgent
            
        Returns:
            LLMResponse with generated text and metadata
        """
        if not self.is_available():
            logger.warning(f"⚠️ LLM not available (api_key missing or too short). Using fallback.")
            return self._fallback_response(user_message, context_documents, sentiment)
        
        try:
            self._rate_limit()
            
            # Build system prompt
            system_prompt = self._build_system_prompt(
                company_name=company_name,
                context_documents=context_documents,
                guidelines=guidelines,
                sentiment=sentiment,
                is_urgent=is_urgent,
                language=language
            )
            
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (last 6 messages, each truncated to save tokens)
            if conversation_history:
                for msg in conversation_history[-6:]:
                    if "role" in msg:
                        role = msg["role"]
                    else:
                        role = "user" if msg.get("sender_type") == "customer" else "assistant"
                    content = msg.get("content", "")
                    if content:
                        # Truncate long messages to save input tokens
                        messages.append({"role": role, "content": content[:200]})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Make API request
            return self._make_request(messages)
            
        except Exception as e:
            logger.error(f"[ERROR] LLM generation failed: {e}")
            return LLMResponse(
                response="I apologize, but I'm having trouble generating a response. Let me connect you with a team member who can help.",
                confidence=0.0,
                model=self.model,
                tokens_used=0,
                success=False,
                error=str(e)
            )
    
    def _make_request(self, messages: List[Dict]) -> LLMResponse:
        """Make API request to any OpenAI-compatible endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "top_p": 0.9,
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    ai_response = data["choices"][0]["message"]["content"]
                    model_used = data.get("model", self.model)
                    tokens_used = data.get("usage", {}).get("total_tokens", 0)
                    
                    self._initialized = True
                    
                    confidence = self._calculate_confidence(ai_response, [])
                    
                    logger.info(f"[OK] {self._provider} response from: {model_used}")
                    
                    return LLMResponse(
                        response=ai_response,
                        confidence=confidence,
                        model=model_used,
                        tokens_used=tokens_used,
                        success=True
                    )
                
                elif response.status_code == 429:
                    logger.warning(f"[WARN] Rate limited (429), retrying after delay...")
                    # Retry once after delay, then try fallback model
                    time.sleep(2.0)  # Wait 2s before retry
                    if self.model != FALLBACK_MODEL:
                        original_model = self.model
                        self.model = FALLBACK_MODEL
                        retry_result = self._make_request(messages)
                        self.model = original_model  # Restore original model
                        return retry_result
                    else:
                        return LLMResponse(
                            response="I'm currently experiencing high demand. Please try again in a moment.",
                            confidence=0.3,
                            model=self.model,
                            tokens_used=0,
                            success=False,
                            error="Rate limited"
                        )
                else:
                    error_msg = response.text[:500]
                    logger.error(f"[ERROR] OpenRouter error {response.status_code}: {error_msg}")
                    return LLMResponse(
                        response="I apologize, but I'm having trouble right now. Let me connect you with a team member.",
                        confidence=0.0,
                        model=self.model,
                        tokens_used=0,
                        success=False,
                        error=f"API error: {response.status_code}"
                    )
                    
        except httpx.TimeoutException:
            logger.error("[ERROR] OpenRouter request timed out")
            return LLMResponse(
                response="I apologize for the delay. Let me connect you with a team member who can help immediately.",
                confidence=0.0,
                model=self.model,
                tokens_used=0,
                success=False,
                error="Request timeout"
            )
    
    def _build_system_prompt(
        self,
        company_name: str,
        context_documents: List[str],
        guidelines: Optional[str],
        sentiment: Optional[str],
        is_urgent: bool,
        language: str = "en"
    ) -> str:
        """Build the system prompt for LLM."""
        has_context = bool(context_documents and any(d.strip() for d in context_documents))

        if has_context:
            # ── RAG MODE: Context documents available → answer from them ──
            prompt = f"""You are a professional yet friendly customer support agent for {company_name}.

CORE RULES:
1. Answer ONLY from the CONTEXT DOCUMENTS provided below. Never invent product names, prices, policies, or features.
2. If the answer is not in the context, honestly say you don't have that specific information and offer to connect the customer with a specialist.
3. Keep responses concise, helpful, and well-structured (1-3 sentences for simple queries, bullet points for complex ones).
4. Use a warm, professional tone — like a knowledgeable colleague, not a robot.
5. If context documents include [IMAGE:...] tags, you MUST include those exact tags in your response so the customer can see the relevant image. Keep the tag on its own line.

"""
        else:
            # ── GENERAL MODE: No context documents → honest assistant ──
            prompt = f"""You are a professional yet friendly customer support agent for {company_name}.

CORE RULES:
1. No product or policy documents have been uploaded yet — you have NO specific info about their catalog, pricing, or policies.
2. For general conversational questions, respond helpfully and warmly.
3. For specific product, price, or policy questions, honestly say you don't have that info yet and offer to connect the customer with the team.
4. Keep responses concise (1-3 sentences). Never make up information.

"""

        # De-escalation for urgent/negative customers
        if is_urgent:
            prompt += """IMPORTANT — CUSTOMER SEEMS UPSET:
- Acknowledge their frustration sincerely ("I completely understand your concerns")
- Prioritize resolution over explanation
- Offer to escalate to a human agent if the issue is complex
- Never be defensive or dismissive

"""

        if guidelines:
            prompt += f"""COMPANY GUIDELINES:
{guidelines}

"""

        if has_context:
            context_str = self._format_context(context_documents)
            prompt += f"""CONTEXT DOCUMENTS (Use these to answer):
{context_str}

Remember: Prefer the context documents above. If unsure, offer to connect to a human agent."""

        # Language instruction — respond in the customer's language
        # V4 FIX — Extended from 6 to 15 languages
        LANG_NAMES = {
            "en": "English", "de": "German", "fr": "French",
            "es": "Spanish", "it": "Italian", "nl": "Dutch",
            # V4 NEW — Urdu, Hindi, Arabic, and 6 more languages
            "ur": "Urdu", "hi": "Hindi", "ar": "Arabic",
            "zh-cn": "Chinese", "pt": "Portuguese", "ru": "Russian",
            "ja": "Japanese", "ko": "Korean", "tr": "Turkish"
        }
        if language != "en" and language in LANG_NAMES:
            prompt += f"""\n\nIMPORTANT: The customer is writing in {LANG_NAMES[language]}. You MUST respond in {LANG_NAMES[language]}."""

        # ★ V4: Order context instruction — when order data is passed via context
        if hasattr(self, '_order_context') and self._order_context:
            prompt += f"""\n\nOrder Information:\n{self._order_context}"""
            prompt += "\nUse this order data to answer the customer's order-related questions accurately."

        return prompt
    
    def _format_context(self, documents: List[str]) -> str:
        """Format context documents for prompt."""
        if not documents:
            return "No relevant documents found."
        
        formatted = []
        for i, doc in enumerate(documents, 1):
            text = doc[:1500] if len(doc) > 1500 else doc
            formatted.append(f"[{i}] {text}")
        
        return "\n\n".join(formatted)
    
    def _calculate_confidence(self, response: str, context: List[str]) -> float:
        """Calculate response confidence score."""
        low_confidence_phrases = [
            "don't have that information",
            "not sure", "uncertain",
            "connect you with", "team member",
            "don't know", "cannot find", "no information"
        ]
        
        response_lower = response.lower()
        
        for phrase in low_confidence_phrases:
            if phrase in response_lower:
                return 0.3
        
        # Good confidence for successful responses
        return 0.8
    
    # Pool of varied fallback responses (never repeat the same static text)
    _FALLBACK_GENERAL = [
        "Hi there! I'd love to help you out. Could you tell me a bit more about what you're looking for?",
        "Hello! Thanks for reaching out. What can I help you with today?",
        "Hey! I'm here to help. Could you share some more details so I can assist you better?",
        "Welcome! How can I assist you today? Feel free to ask me anything.",
        "Hi! Great to hear from you. Let me know how I can help — I'm all ears!",
        "Hello! I'd be happy to assist. What's on your mind?",
        "Hey there! Thanks for stopping by. What can I do for you?",
    ]
    _FALLBACK_NEGATIVE = [
        "I hear you, and I'm sorry you're dealing with this. Let me see how I can help right away.",
        "I completely understand your concerns. Let me look into this for you immediately.",
        "I'm sorry you're having this experience. Your concern is important — let me help.",
        "I understand this situation. Let me do my best to resolve this for you.",
    ]

    def _fallback_response(
        self,
        user_message: str,
        context_documents: List[str],
        sentiment: Optional[str]
    ) -> LLMResponse:
        """Generate varied fallback response when LLM is not available."""
        if context_documents:
            best_context = context_documents[0][:500] if context_documents else ""
            if sentiment == "negative":
                response = f"I understand your concern. Based on our information: {best_context}... Would you like me to connect you with a specialist?"
            else:
                response = f"Based on our information: {best_context}... Is there anything specific you'd like me to clarify?"
        else:
            if sentiment == "negative":
                response = random.choice(self._FALLBACK_NEGATIVE)
            else:
                response = random.choice(self._FALLBACK_GENERAL)

        return LLMResponse(
            response=response,
            confidence=0.4,
            model="fallback-template",
            tokens_used=0,
            success=True
        )
    
    def get_model_info(self) -> Dict:
        """Get information about the LLM configuration."""
        return {
            "model": self.model,
            "provider": self._provider,
            "api_configured": self.api_key is not None,
            "initialized": self._initialized,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "base_url": self.base_url
        }
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """List example models available on popular providers."""
        return {
            "fal.ai": [
                "deepseek-r1",
                "deepseek-v3",
            ],
            "openrouter (free)": [
                "meta-llama/llama-3.3-70b-instruct:free",
                "mistralai/mistral-7b-instruct:free",
                "google/gemma-2-9b-it:free",
            ],
            "openai": [
                "gpt-4o",
                "gpt-4o-mini",
            ],
            "anthropic": [
                "claude-sonnet-4-20250514",
                "claude-3-5-haiku-20241022",
            ],
        }


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService()
    
    return _llm_service
