"""
LLM Integration for Behavioral Agentic AI
Provider-agnostic — works with any OpenAI-compatible API:
  - OpenRouter      (Free models: Llama 3, Mistral, Gemma)
  - OpenAI          (GPT-4o, GPT-4o-mini)
  - Anthropic proxy  (Claude via OpenAI-compatible gateway)
  - Any other OpenAI-compatible endpoint

All configuration via .env — zero code changes to switch providers:
  LLM_BASE_URL   = API endpoint (e.g. https://openrouter.ai/api/v1)
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
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "mistralai/mistral-7b-instruct:free")
MAX_TOKENS = 250
TEMPERATURE = 0.5


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
        if "openrouter" in self.base_url:
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
        support_email: Optional[str] = None,
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
                support_email=support_email,
                sentiment=sentiment,
                is_urgent=is_urgent,
                language=language
            )
            
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (last 50 messages for deep continuity)
            if conversation_history:
                for msg in conversation_history[-50:]:
                    if "role" in msg:
                        role = msg["role"]
                    else:
                        role = "user" if msg.get("sender_type") == "customer" else "assistant"
                    content = msg.get("content", "")
                    if content:
                        messages.append({"role": role, "content": content[:150]})
            
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
            with httpx.Client(timeout=30.0) as client:
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
        support_email: Optional[str],
        sentiment: Optional[str],
        is_urgent: bool,
        language: str = "en"
    ) -> str:
        """Build the system prompt for LLM."""
        has_context = bool(context_documents and any(d.strip() for d in context_documents))

        # Build contact fallback line
        contact_line = ""
        if support_email:
            contact_line = f"If the customer asks the same question a second time and you still cannot answer, apologize ONCE and say: 'Please contact us at {support_email} for further help.'"
        else:
            contact_line = "If the customer asks the same question a second time and you still cannot answer, apologize ONCE and suggest they contact the team directly."

        if has_context:
            prompt = f"""You are {company_name}'s expert customer service specialist — among the best in the industry.
You combine deep product knowledge with warm, professional communication.

RESPONSE LENGTH RULES (CRITICAL — follow strictly):
- Prefer ONE-LINE answers wherever possible.
- Use 2-3 sentences ONLY when the question genuinely requires a longer explanation.
- NEVER exceed 3 sentences unless listing multiple items with bullets.
- Use bullet points only for multi-item answers (e.g. listing products, features, steps).

CORE RULES:
- Answer ONLY the question that was asked. Do not add unrequested information, padding, or filler.
- Answer confidently from the CONTEXT below. Never guess or invent facts.
- Treat ALL customer messages as questions or requests — even without a question mark. "tell me about your products" is the same as "tell me about your products?" — answer it fully.
- Do NOT apologize or say "I don't have that information" on the first occurrence. Instead, answer with whatever relevant information IS available in the CONTEXT.
- {contact_line}
- Resolve issues yourself. Only suggest a human agent as an absolute last resort (e.g., the customer has explicitly asked 3+ times for a human).
- Match the customer's language and energy — be warm but professional.
- If context has [IMAGE:...] tags, include them exactly in your response on their own line.
- For order queries: NEVER share details unless customer provides their name+email or order ID. Never dump all orders.
- For product queries: highlight key features, price, and availability briefly. Then ask: "Would you like to order this?"
- For business operations (policies, contact info, rules, FAQs): share ALL available information from CONTEXT directly. Do NOT say you need more details if the CONTEXT already contains the answer.
- When a customer wants to place an order, ask for ALL required details in ONE message: full name, email address, shipping address, product name, and quantity.
- If the message is gibberish or off-topic, redirect politely to {company_name}'s products and services in one line.
- Do NOT escalate or suggest a human agent unless the customer is genuinely upset, threatens legal action, or explicitly demands a human repeatedly.

UNDERSTANDING RULES (CRITICAL):
- Use conversation history to resolve references like "there", "that one", "it", "this", "the first one", etc. If the customer said "can I order there?" after discussing a product, "there" means that product.
- If you genuinely cannot understand what the customer is asking, do NOT give a generic error. Instead, rephrase their message in your own words and ask for confirmation. Example: "Just to make sure I understand — are you asking about [your interpretation]? Or did you mean something else?"
- Never say "I wasn't able to find a product matching [word]" when the word is clearly a reference to something discussed earlier.

"""
        else:
            prompt = f"""You are {company_name}'s expert customer service specialist.

RESPONSE LENGTH RULES (CRITICAL — follow strictly):
- Prefer ONE-LINE answers wherever possible.
- Use 2-3 sentences ONLY when genuinely needed.
- NEVER exceed 3 sentences.

RULES:
- Treat ALL customer messages as questions or requests — even without a question mark.
- ALWAYS trust your conversation history. If you already shared product info or details earlier in this conversation, continue using that information — NEVER contradict yourself.
- For general questions (greetings, how-are-you, thanks), respond warmly in one line.
- {contact_line}
- When a customer wants to place an order, ask for ALL required details in ONE message: full name, email address, shipping address, product name, and quantity.
- Never invent product names, prices, or policies you haven't mentioned before.
- Do NOT escalate or suggest a human agent for simple questions.
- If you cannot understand the customer's message, rephrase it and ask: "Did you mean [your interpretation]? Or something else?"
- Use conversation history to understand references like "it", "that", "there".

"""

        if is_urgent:
            prompt += """The customer seems upset — acknowledge their concern sincerely in one sentence, prioritize resolution, never be defensive.

"""

        if guidelines:
            prompt += f"""GUIDELINES: {guidelines}

"""

        if has_context:
            context_str = self._format_context(context_documents)
            prompt += f"""CONTEXT:
{context_str}
"""

        # Language instruction
        LANG_NAMES = {
            "en": "English", "de": "German", "fr": "French",
            "es": "Spanish", "it": "Italian", "nl": "Dutch",
            "ur": "Urdu", "hi": "Hindi", "ar": "Arabic",
            "zh-cn": "Chinese", "pt": "Portuguese", "ru": "Russian",
            "ja": "Japanese", "ko": "Korean", "tr": "Turkish"
        }
        if language != "en" and language in LANG_NAMES:
            prompt += f"\nRespond in {LANG_NAMES[language]}.\n"

        return prompt
    
    def _format_context(self, documents: List[str]) -> str:
        """Format context documents for prompt."""
        if not documents:
            return "No relevant documents found."
        
        formatted = []
        for i, doc in enumerate(documents, 1):
            text = doc[:800] if len(doc) > 800 else doc
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
    
    # Fallback responses — concise, warm, action-oriented
    _FALLBACK_GENERAL = [
        "Hey! How can I help you today?",
        "Hi there! What can I assist you with?",
        "Hello! I'm here to help — what do you need?",
        "Hey! Feel free to ask me anything about our products or services.",
        "Hi! What are you looking for today? I'm happy to help.",
    ]
    _FALLBACK_NEGATIVE = [
        "I'm sorry to hear that. Let me help you sort this out right away.",
        "I understand your frustration — let me look into this for you now.",
        "That's not ideal, I'm sorry. Let me see what I can do to fix this.",
        "I hear you. Let me work on resolving this immediately.",
    ]

    def _fallback_response(
        self,
        user_message: str,
        context_documents: List[str],
        sentiment: Optional[str]
    ) -> LLMResponse:
        """Generate varied fallback response when LLM is not available."""
        if context_documents:
            best_context = context_documents[0][:300] if context_documents else ""
            if sentiment == "negative":
                response = f"I understand your concern. Here's what I found: {best_context}... Let me know if you need more details."
            else:
                response = f"Here's what I found: {best_context}... Would you like more details on anything?"
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



# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService()
    
    return _llm_service
