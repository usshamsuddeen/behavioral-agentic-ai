"""
Widget API — Zone 6: Customer-Facing Chat Endpoints
FRD v4.0 (FR-6.1, FR-6.2)

These endpoints are called by the embeddable JS widget on client stores.
Auth: Widget API key (not JWT) — FR-7.1.6

Endpoints:
    GET  /{api_key}/config              — Load widget appearance/behavior config
    POST /{api_key}/session             — Start a new chat session (pre-chat form)
    POST /{api_key}/chat                — Customer sends a message → full AI pipeline
    GET  /{api_key}/history             — Reload conversation on page refresh
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageSender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/widget", tags=["Widget (Customer-Facing)"])


# ═══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class StartSessionRequest(BaseModel):
    """Pre-chat form data to start a session"""
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """Customer sends a message"""
    session_id: str
    message: str
    customer_name: Optional[str] = None  # embed.js sends this


# ═══════════════════════════════════════════════════════════════════
# HELPER: Validate Widget API Key — FR-7.1.6
# ═══════════════════════════════════════════════════════════════════

def get_tenant_by_api_key(api_key: str, db: Session) -> Tenant:
    """Look up tenant by widget API key. Raises 404 if invalid."""
    tenant = db.query(Tenant).filter(
        Tenant.widget_api_key == api_key,
        Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or inactive widget key"
        )
    return tenant


# ═══════════════════════════════════════════════════════════════════
# GET WIDGET CONFIG (FR-6.1.7)
# ═══════════════════════════════════════════════════════════════════

@router.get("/{api_key}/config")
async def get_widget_config(
    api_key: str,
    db: Session = Depends(get_db)
):
    """
    Load widget configuration for rendering.
    Called by embed.js on page load.

    Returns FLAT config object — embed.js reads fields like
    config.theme_color, config.bot_name, config.is_active directly.
    """
    tenant = get_tenant_by_api_key(api_key, db)

    widget_config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()

    if not widget_config:
        # Return sensible defaults so the widget still renders
        return {
            "position": "bottom-right",
            "theme_color": "#6366f1",
            "welcome_message": "Hi! How can I help you today?",
            "bot_name": "AI Assistant",
            "pre_chat_form_enabled": False,
            "pre_chat_fields": ["name", "email"],
            "placeholder_text": "Type your message...",
            "show_branding": True,
            "branding_logo_url": None,
            "is_active": True,
            "widget_type": "full",  # ★ V4
            "tenant_name": tenant.name,
        }

    # ── FLAT response: embed.js reads config.theme_color etc. directly ──
    return {
        "position": widget_config.position or "bottom-right",
        "theme_color": widget_config.theme_color or "#6366f1",
        "welcome_message": widget_config.welcome_message or "Hi! How can I help you today?",
        "bot_name": widget_config.bot_name or "AI Assistant",
        "pre_chat_form_enabled": widget_config.pre_chat_form_enabled or False,
        "pre_chat_fields": widget_config.get_pre_chat_fields(),
        "placeholder_text": getattr(widget_config, 'placeholder_text', None) or "Type your message...",
        "show_branding": getattr(widget_config, 'show_branding', True),
        "branding_logo_url": widget_config.branding_logo_url,
        "is_active": widget_config.is_active,
        "widget_type": getattr(widget_config, 'widget_type', 'full') or "full",  # ★ V4
        "tenant_name": tenant.name,
    }


# ═══════════════════════════════════════════════════════════════════
# START CHAT SESSION (FR-6.2)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{api_key}/session")
async def start_chat_session(
    api_key: str,
    data: StartSessionRequest = StartSessionRequest(),
    db: Session = Depends(get_db)
):
    """
    Start a new chat session for a customer.
    Optionally receives pre-chat form data (name, email).
    Returns session_id for subsequent messages.

    embed.js reads: data.session_id, data.welcome_message
    """
    tenant = get_tenant_by_api_key(api_key, db)

    # Auto-number anonymous visitors: "Visitor" → "Visitor #N"
    visitor_name = data.customer_name
    if not visitor_name or visitor_name.strip().lower() == "visitor":
        existing_count = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id
        ).count()
        visitor_name = f"Visitor #{existing_count + 1}"

    # Create conversation record
    conversation = Conversation(
        tenant_id=tenant.id,
        session_id=Conversation.generate_session_id(),
        customer_name=visitor_name,
        customer_email=data.customer_email,
        status=ConversationStatus.ACTIVE.value,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Fetch widget config for welcome message
    widget_config = db.query(WidgetConfig).filter(
        WidgetConfig.tenant_id == tenant.id
    ).first()
    welcome_msg = widget_config.welcome_message if widget_config else "Hi! How can I help you today?"
    bot_name = widget_config.bot_name if widget_config else "AI Assistant"

    # Save welcome message as first AI message
    welcome = Message(
        tenant_id=tenant.id,
        conversation_id=conversation.id,
        content=welcome_msg,
        sender_type=MessageSender.AI.value,
        sender_name=bot_name,
        sentiment="positive",
        sentiment_score=0.8,
        sentiment_label="Happy",
    )
    db.add(welcome)
    conversation.message_count = 1
    db.commit()

    logger.info(
        f"Widget session started: {conversation.session_id} "
        f"for tenant {tenant.name} (customer: {data.customer_name or 'anonymous'})"
    )

    return {
        "session_id": conversation.session_id,
        "conversation_id": conversation.id,
        "welcome_message": {
            "content": welcome_msg,
            "sender": "ai",
            "sender_name": bot_name,
            "timestamp": welcome.created_at.isoformat() if welcome.created_at else datetime.utcnow().isoformat()
        }
    }


# ═══════════════════════════════════════════════════════════════════
# SEND CHAT MESSAGE (FR-6.2.9) — The core endpoint
# Full pipeline: Save → Sentiment → History → RAG → LLM → Escalation → Prediction
# ═══════════════════════════════════════════════════════════════════

@router.post("/{api_key}/chat")
async def send_chat_message(
    api_key: str,
    data: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Customer sends a message via the widget.

    Pipeline:
        1. Save customer message
        2. Sentiment Analysis (FR-5.1 — BERT → VADER → Dictionary)
        3. Update frustration level (moving average)
        4. Escalation Check (FR-5.3 — keywords, threshold, patterns)
        5. Load conversation history for AI context
        6. RAG + LLM Response (FR-5.2 — retrieve KB chunks → generate)
        7. Behavioral Prediction (FR-5.4 — churn risk, purchase intent)
        8. Save AI response
        9. WebSocket push on escalation (FR-5.3.11)

    embed.js expects:
        { response: "string", is_escalated: bool, is_human_agent: bool }
    """
    tenant = get_tenant_by_api_key(api_key, db)

    # ── Find conversation by session_id ──
    conversation = db.query(Conversation).filter(
        Conversation.session_id == data.session_id,
        Conversation.tenant_id == tenant.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid session. Please start a new chat."
        )

    # If conversation is escalated, resolved, or closed — don't auto-respond with AI.
    # Only ACTIVE and PENDING conversations get AI responses.
    # This covers: escalated (even before agent assignment), human takeover, resolved, closed.
    is_human_takeover = (
        conversation.status in (
            ConversationStatus.ESCALATED.value,
            ConversationStatus.RESOLVED.value,
            ConversationStatus.CLOSED.value,
        )
        or conversation.assigned_agent_id is not None
    )

    # ══════════════════════════════════════════════════════════════
    # Step 1: Save customer message
    # ══════════════════════════════════════════════════════════════
    customer_msg = Message(
        tenant_id=tenant.id,
        conversation_id=conversation.id,
        content=data.message,
        sender_type=MessageSender.CUSTOMER.value,
        sender_name=data.customer_name or conversation.customer_name or "Customer",
    )

    # ══════════════════════════════════════════════════════════════
    # Step 2: Sentiment Analysis (FR-5.1)
    # Uses 3-tier fallback: BERT → VADER → Dictionary
    # ══════════════════════════════════════════════════════════════
    detected_lang = "en"
    try:
        from app.services.language import detect_language
        lang_result = detect_language(data.message)
        detected_lang = lang_result.get("code", "en")
    except Exception:
        pass

    sentiment_result = {"sentiment": "neutral", "score": 0.5, "label": "Neutral", "language": detected_lang}
    try:
        from app.services.sentiment import analyze_sentiment
        sentiment_result = analyze_sentiment(data.message, detected_lang)

        customer_msg.sentiment = sentiment_result.get("sentiment", "neutral")
        customer_msg.sentiment_score = sentiment_result.get("score", 0.5)
        customer_msg.sentiment_label = sentiment_result.get("label", "Neutral")
        customer_msg.detected_language = detected_lang

        # Update conversation-level sentiment
        conversation.current_sentiment = customer_msg.sentiment
        conversation.sentiment_score = customer_msg.sentiment_score
        if customer_msg.detected_language:
            conversation.detected_language = customer_msg.detected_language
    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {e}")
        customer_msg.sentiment = "neutral"
        customer_msg.sentiment_score = 0.5

    # ══════════════════════════════════════════════════════════════
    # Step 3: Update frustration level (moving average)
    # Frustration = 1.0 - normalized_score, averaged with history
    # ══════════════════════════════════════════════════════════════
    current_frustration = conversation.frustration_level or 0.0
    raw_score = customer_msg.sentiment_score if customer_msg.sentiment_score is not None else 0.5
    # Normalize: BERT returns [-1, +1], but frustration needs [0, 1].
    # Map: -1 → 0, 0 → 0.5, +1 → 1.0
    normalized_score = (raw_score + 1.0) / 2.0 if raw_score < 0 else raw_score
    normalized_score = min(1.0, max(0.0, normalized_score))
    # Exponential moving average: weight recent messages more heavily
    alpha = 0.4  # smoothing factor — higher = more weight on current message
    new_frustration = alpha * (1.0 - normalized_score) + (1.0 - alpha) * current_frustration
    conversation.frustration_level = round(min(1.0, max(0.0, new_frustration)), 4)

    db.add(customer_msg)
    conversation.message_count = (conversation.message_count or 0) + 1
    conversation.last_message_preview = data.message[:200]
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer_msg)

    # ══════════════════════════════════════════════════════════════
    # Step 4: Load conversation history for AI context
    # Gives the LLM memory of the conversation so far
    # MUST be loaded before the AI agent call (Step 5) — previously
    # this was Step 5 and caused a NameError when escalation tried
    # to reference conversation_history before it was defined.
    # ══════════════════════════════════════════════════════════════
    conversation_history = []
    try:
        recent_messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(20).all()  # Last 20 messages

        # Reverse to chronological order, skip current customer message
        for msg in reversed(recent_messages):
            if msg.id == customer_msg.id:
                continue  # Skip the message we just saved — it's in user_message
            role = "assistant" if msg.sender_type in (MessageSender.AI.value, MessageSender.AGENT.value) else "user"
            conversation_history.append({
                "role": role,
                "content": msg.content,
            })
    except Exception as e:
        logger.warning(f"Failed to load conversation history: {e}")

    # ══════════════════════════════════════════════════════════════
    # ★ V4 STEP 4.5: Intent Classification (Zone 5)
    # Routes messages to the most efficient handler.
    # ORDER_QUERY → SQL lookup (bypasses RAG + LLM)
    # HUMAN_REQUEST → Direct escalation (bypasses LLM)
    # Others → continue to RAG + LLM pipeline
    # ══════════════════════════════════════════════════════════════
    # ── Defaults — MUST be set before conditional branches ──
    ai_response_text = ""
    should_escalate = False
    escalation_info = {}
    intent_skipped_agent = False
    try:
        from app.services.intent_router import (
            classify_intent, INTENT_ORDER_QUERY, INTENT_HUMAN_REQUEST,
            INTENT_ORDER_VERIFY, INTENT_PRODUCT_INFO, INTENT_PURCHASE
        )
        widget_config_for_intent = db.query(WidgetConfig).filter(
            WidgetConfig.tenant_id == tenant.id
        ).first()
        widget_type = getattr(widget_config_for_intent, 'widget_type', 'full') or 'full'
        intent_result = classify_intent(
            text=data.message,
            widget_type=widget_type,
            sentiment=sentiment_result.get("sentiment")
        )
        intent = intent_result["intent"]
        logger.info(f"🎯 Intent: {intent} (confidence: {intent_result['confidence']:.2f}) — {intent_result['reason']}")

        if intent == INTENT_ORDER_QUERY:
            # ★ Direct SQL lookup — bypass RAG + LLM for speed
            try:
                from app.services.order_query import lookup_order
                order_id = intent_result["extracted_data"].get("order_id")
                customer_email = getattr(data, 'customer_email', None) or conversation.customer_email
                order_response = lookup_order(
                    order_id=order_id,
                    email=customer_email,
                    tenant_id=tenant.id,
                    db=db
                )
                ai_response_text = order_response["response"]
                intent_skipped_agent = True
                logger.info(f"📦 Order lookup completed (skipped RAG+LLM)")
            except Exception as oq_err:
                logger.warning(f"Order lookup failed, falling back to agent: {oq_err}")

        elif intent == INTENT_HUMAN_REQUEST:
            # ★ Direct escalation — bypass LLM
            ai_response_text = "I understand you'd like to speak with a human agent. Let me connect you right away."
            should_escalate = True
            escalation_info = {"reason": "Customer requested human agent", "triggers": ["human_request"]}
            intent_skipped_agent = True
            logger.info(f"🧑 Human request — forcing escalation (skipped RAG+LLM)")

        elif intent == INTENT_PURCHASE:
            # ★ V5: Widget-based ordering
            # Only place order immediately if we have REAL customer details.
            # Otherwise, let the LLM ask the customer for name, email, address.
            try:
                from app.services.order_placement import place_widget_order
                import re as _re

                product_query = intent_result["extracted_data"].get("product_query", "").strip()

                # ── Resolve contextual references ("this", "that", "it", empty) ──
                PRONOUNS = {"this", "that", "it", "one", "these", "those", "them", ""}
                if product_query.lower().strip(".,!? ") in PRONOUNS:
                    resolved_product = None
                    recent = (conversation_history or [])[-10:]
                    for msg in reversed(recent):
                        if msg.get("role") != "assistant":
                            continue
                        content = msg.get("content", "")
                        # Pattern 1: **Product:** Name
                        p_match = _re.search(r'\*\*(?:Product|Item)[:\s]*\*\*\s*(.+?)(?:\n|$)', content, _re.IGNORECASE)
                        if p_match:
                            resolved_product = p_match.group(1).strip().strip('*')
                            break
                        # Pattern 2: "Product Name ($45)"
                        p_match = _re.search(r'[•\-]\s*(.+?)\s*\(\$?\s*[\d,.]+\)', content)
                        if p_match:
                            resolved_product = p_match.group(1).strip().strip('*')
                            break
                        # Pattern 3: "Our/The Product Name ($45)"
                        p_match = _re.search(r'(?:Our|The)\s+(.+?)\s+\(\$?\s*[\d,.]+\)', content, _re.IGNORECASE)
                        if p_match:
                            resolved_product = p_match.group(1).strip().strip('*')
                            break

                    if resolved_product:
                        product_query = resolved_product
                        logger.info(f"🔗 Resolved pronoun to product: '{product_query}'")
                    else:
                        logger.info("🔗 Could not resolve product reference, falling through to LLM")
                        product_query = None

                # ── Check if customer details are available ──
                has_name = conversation.customer_name and conversation.customer_name.strip() and conversation.customer_name.strip().lower() not in ("widget customer", "guest", "customer", "unknown", "")
                has_email = conversation.customer_email and conversation.customer_email.strip() and "@" in (conversation.customer_email or "")

                if product_query and has_name and has_email:
                    # ✅ Have customer details AND product — place order now
                    order_result = place_widget_order(
                        tenant_id=tenant.id,
                        customer_name=conversation.customer_name.strip(),
                        customer_email=conversation.customer_email.strip(),
                        product_query=product_query,
                        conversation_id=conversation.id,
                        db=db
                    )
                    ai_response_text = order_result["response"]
                    intent_skipped_agent = True
                    logger.info(f"🛍️ Purchase intent handled: success={order_result.get('success')}")
                else:
                    # ❌ Missing customer details — let LLM ask for them
                    logger.info(
                        f"🛍️ Purchase intent detected but missing details "
                        f"(name={has_name}, email={has_email}, product={'✓' if product_query else '✗'}) "
                        f"— falling through to LLM to collect info"
                    )
                    # Fall through to LLM agent (intent_skipped_agent stays False)
            except Exception as purchase_err:
                logger.warning(f"Purchase handler failed, falling back to agent: {purchase_err}")

    except Exception as intent_err:
        logger.warning(f"Intent router failed (non-blocking): {intent_err}")

    # ══════════════════════════════════════════════════════════════
    # Step 4.6: Product Catalog Injection
    # When the message is product-related, query ALL products from DB
    # and inject as pre-built context. RAG semantic search often misses
    # products because "show all products" doesn't semantically match
    # individual product descriptions.
    # ══════════════════════════════════════════════════════════════
    product_context_override = None
    try:
        msg_lower = data.message.lower()
        PRODUCT_SIGNALS = [
            "product", "catalog", "catalogue", "menu", "item",
            "what do you sell", "what do you have", "what do you offer",
            "show me", "list", "available", "price", "how much",
        ]
        is_product_query = any(sig in msg_lower for sig in PRODUCT_SIGNALS)
        # Also check if intent router classified as PRODUCT_INFO
        if not is_product_query:
            try:
                is_product_query = (intent == INTENT_PRODUCT_INFO)
            except NameError:
                pass

        if is_product_query:
            from app.models.product_listing import ProductListing
            all_products = db.query(ProductListing).filter(
                ProductListing.tenant_id == tenant.id
            ).all()
            if all_products:
                product_names = [p.name for p in all_products]
                lines = [f"PRODUCT CATALOG — {len(all_products)} products total (this is the COMPLETE catalog, list ALL of them):\n"]
                for p in all_products:
                    line = f"Product: {p.name}\n"
                    line += f"  Price: {p.currency or 'USD'} {p.price}\n"
                    line += f"  In Stock: {'Yes' if p.in_stock else 'No'}\n"
                    if p.description:
                        line += f"  Description: {p.description}\n"
                    if p.category:
                        line += f"  Category: {p.category}\n"
                    images = p.get_images() if hasattr(p, 'get_images') else []
                    if images and images[0]:
                        line += f"  [IMAGE:{images[0]}]\n"
                    lines.append(line)
                product_context_override = "\n".join(lines)
                logger.info(f"📦 Injected full product catalog ({len(all_products)} products: {product_names}) into context")
    except Exception as pc_err:
        logger.warning(f"Product catalog injection failed (non-blocking): {pc_err}")

    # ══════════════════════════════════════════════════════════════
    # Step 5: Generate AI Response via Agent (FR-5.2 + FR-5.3)
    # The AI agent internally handles:
    #   - RAG retrieval (knowledge base context)
    #   - LLM response generation
    #   - Escalation detection (keywords, sentiment, frustration)
    # This is the SINGLE source of truth for escalation decisions.
    # Previously, escalation was checked twice (here AND in agent.py)
    # which caused false triggers on normal messages.
    # ══════════════════════════════════════════════════════════════
    ai_response_text = ai_response_text if intent_skipped_agent else "I'm here to help! Let me look into that for you."
    confidence = 0.5 if not intent_skipped_agent else 0.85
    should_escalate = should_escalate if intent_skipped_agent else False
    escalation_info = escalation_info if intent_skipped_agent else {}

    if is_human_takeover:
        # Human agent has taken over — don't auto-respond with AI
        ai_response_text = None
    elif not intent_skipped_agent:
        # Unified flow — agent handles RAG + LLM + escalation internally
        try:
            from app.ai.agent import get_ai_agent, AgentContext, AgentAction
            agent = get_ai_agent()
            agent_context = AgentContext(
                client_id=str(tenant.id),
                conversation_id=str(conversation.id),
                user_message=data.message,
                conversation_history=conversation_history,
                company_name=tenant.name or "Our Store",
                company_guidelines=tenant.ai_restrictions,
                support_email=tenant.support_email,
                current_frustration=conversation.frustration_level or 0.0,
                detected_language=detected_lang,
                pre_sentiment={
                    "sentiment": sentiment_result.get("sentiment", "neutral"),
                    "score": sentiment_result.get("score", 0.5),
                    "confidence": sentiment_result.get("confidence", 0.5),
                    "label": sentiment_result.get("label", "neutral"),
                    "is_urgent": sentiment_result.get("is_urgent", False),
                },
                product_context=product_context_override,
            )
            result = agent.process_message(agent_context)
            ai_response_text = result.response
            confidence = result.confidence

            # Use agent's escalation decision (single source of truth)
            # IMPORTANT: Only use the hard ESCALATE action for full escalation flow.
            # requires_human is a SOFT flag (human review recommended) — it should NOT
            # trigger escalation records, WebSocket alerts, or status changes.
            # It was causing false escalations when confidence was low (no KB docs).
            if result.action == AgentAction.ESCALATE:
                should_escalate = True
                escalation_info = result.escalation

                # Calculate priority
                from app.services.escalation import calculate_escalation_priority
                priority = calculate_escalation_priority(
                    sentiment_score=customer_msg.sentiment_score or 0.5,
                    frustration_level=conversation.frustration_level or 0.0,
                    message_count=conversation.message_count or 1,
                    has_triggers=bool(result.escalation.get("triggers"))
                )

                # Update conversation state
                conversation.is_escalated = True
                conversation.escalation_reason = str(result.escalation.get("reason", "Agent-determined escalation"))
                conversation.escalated_at = datetime.utcnow()
                conversation.status = ConversationStatus.ESCALATED.value
                conversation.priority = priority
                customer_msg.is_escalation_trigger = True
                customer_msg.trigger_keywords = str(result.escalation.get("triggers", []))

                # Create dedicated Escalation record (FRD §12)
                try:
                    from app.models.escalation import Escalation

                    escalation_record = Escalation(
                        conversation_id=conversation.id,
                        tenant_id=tenant.id,
                        priority=priority,
                        trigger_score=result.escalation.get("priority_score", 0.0),
                        sentiment_at_escalation=customer_msg.sentiment,
                        sentiment_score_at_escalation=customer_msg.sentiment_score,
                        frustration_at_escalation=conversation.frustration_level,
                        status="open",
                    )
                    escalation_record.set_trigger_reasons(result.escalation.get("triggers", []))

                    # Build handoff package (FR-5.3.10)
                    handoff = {
                        "conversation_id": conversation.id,
                        "session_id": data.session_id,
                        "customer_name": conversation.customer_name,
                        "customer_email": conversation.customer_email,
                        "message_count": conversation.message_count,
                        "current_sentiment": customer_msg.sentiment,
                        "frustration_level": conversation.frustration_level,
                        "trigger_message": data.message,
                        "trigger_reasons": result.escalation.get("triggers", []),
                        "priority": priority,
                        "recent_messages": conversation_history[-5:] if conversation_history else [],
                    }
                    escalation_record.set_handoff_package(handoff)

                    db.add(escalation_record)
                except Exception as esc_err:
                    logger.warning(f"Failed to create Escalation record: {esc_err}")

                db.commit()

                logger.warning(
                    f"ESCALATION: tenant={tenant.name} session={data.session_id} "
                    f"priority={priority} reasons={result.escalation.get('reason', 'N/A')}"
                )
        except Exception as e:
            logger.error(f"❌ AI agent failed: {type(e).__name__}: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════════════
    # Step 6b: Chat-Confirmed Order Detection
    # When the LLM guides a customer through ordering via conversation
    # (not keyword-triggered INTENT_PURCHASE), detect if the AI response
    # contains order confirmation details and persist to DB + vector store.
    # Also extracts customer name/email from conversation history.
    # ══════════════════════════════════════════════════════════════
    if ai_response_text and not intent_skipped_agent:
        try:
            import re as _re
            # Detect if the AI response looks like an order confirmation
            response_lower = ai_response_text.lower()
            has_order_confirmation = any(marker in response_lower for marker in [
                "order placed successfully",
                "order confirmed",
                "order has been confirmed",
                "order is confirmed",
                "order has been placed",
                "confirmed your order",
                "proceeding with your order",
                "processing your order",
                "your order #",
                "your order id",
                "order id:",
                "✅ **order",
                "confirmation email",
                "order is being processed",
            ])

            if has_order_confirmation:
                # ── Extract product name (multi-strategy) ──
                product_query = None

                # Strategy 1: from AI confirmation response text
                for pattern in [
                    r'\*\*(?:Product|Item)[:\s]*\*\*\s*(.+?)(?:\n|$)',
                    r'order for (?:the\s+)?(.+?)(?:\s*\(|\s*[\-,\n]|\s*!|\s*\.)',
                    r'ordered?\s+(?:the\s+)?(.+?)(?:\s*\(|\s*[\-,\n]|\s*!|\s*\.)',
                ]:
                    p_match = _re.search(pattern, ai_response_text, _re.IGNORECASE)
                    if p_match:
                        candidate = p_match.group(1).strip().strip('*').strip()
                        # Filter out common non-product words
                        if len(candidate) > 2 and candidate.lower() not in ("this", "that", "it", "your", "the"):
                            product_query = candidate
                            break

                # Strategy 2: from conversation history (find last product discussed)
                if not product_query:
                    for msg in reversed(conversation_history or []):
                        if msg.get("role") != "assistant":
                            continue
                        content = msg.get("content", "")
                        # "Aero-Flow Running Tee (USD 45)" pattern
                        p_match = _re.search(r'(?:^|\n)\s*[-•]\s*(.+?)\s*\((?:USD|EUR|GBP|\$)?\s*[\d,.]+\)', content)
                        if p_match:
                            product_query = p_match.group(1).strip().strip('*')
                            break
                        # "**Product:** Name" pattern
                        p_match = _re.search(r'\*\*(?:Product|Item)[:\s]*\*\*\s*(.+?)(?:\n|$)', content, _re.IGNORECASE)
                        if p_match:
                            product_query = p_match.group(1).strip().strip('*')
                            break
                        # "Our/The Product Name (price)" pattern
                        p_match = _re.search(r'(?:Our|The)\s+(.+?)\s+\((?:USD|EUR|GBP|\$)?\s*[\d,.]+', content, _re.IGNORECASE)
                        if p_match:
                            product_query = p_match.group(1).strip().strip('*')
                            break
                        # "Aero-Flow Running Tee (1 piece)" from confirmation summary
                        p_match = _re.search(r'[-•]\s*(.+?)\s*\(\d+\s*(?:piece|qty|quantity|x)\)', content, _re.IGNORECASE)
                        if p_match:
                            product_query = p_match.group(1).strip().strip('*')
                            break

                # Check if order was already created by INTENT_PURCHASE handler
                order_id_match = _re.search(
                    r'(?:order\s*(?:id|#|number)[:\s]*#?\s*)([A-Z0-9\-]+)',
                    ai_response_text, _re.IGNORECASE
                )
                existing_order_id = order_id_match.group(1) if order_id_match else None

                # ── Extract customer details from conversation history ──
                extracted_name = conversation.customer_name
                extracted_email = conversation.customer_email or ""

                all_messages = (conversation_history or []) + [{"role": "user", "content": data.message}]
                for msg in all_messages:
                    content = msg.get("content", "")
                    # Find email in any message
                    email_match = _re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', content)
                    if email_match:
                        extracted_email = email_match.group(0)
                    # Find name patterns — look for user messages with name-like content
                    if msg.get("role") == "user":
                        # Pattern: "my name is John Doe" or "I'm John Doe"
                        name_match = _re.search(r'(?:(?:my\s+)?name\s+is\s+|i\'?m\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', content, _re.IGNORECASE)
                        if name_match:
                            extracted_name = name_match.group(1).strip()
                        # Pattern: comma-separated "Name, email, address"
                        elif "," in content and "@" in content:
                            parts = content.split(",")
                            potential_name = parts[0].strip()
                            if 2 <= len(potential_name.split()) <= 4 and "@" not in potential_name:
                                extracted_name = potential_name
                    # Also check AI's confirmation summary for name
                    if msg.get("role") == "assistant":
                        name_from_ai = _re.search(r'(?:Name|Customer)[:\s]*\*?\*?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', msg.get("content", ""))
                        if name_from_ai:
                            extracted_name = name_from_ai.group(1).strip()

                # Update conversation record with extracted details
                if extracted_name and extracted_name != conversation.customer_name:
                    conversation.customer_name = extracted_name
                if extracted_email and extracted_email != conversation.customer_email:
                    conversation.customer_email = extracted_email
                db.commit()

                # Only create order if it wasn't already created by INTENT_PURCHASE
                if product_query and (not existing_order_id or not existing_order_id.startswith("WO-")):
                    from app.services.order_placement import place_widget_order
                    order_result = place_widget_order(
                        tenant_id=tenant.id,
                        customer_name=extracted_name or "Widget Customer",
                        customer_email=extracted_email or "",
                        product_query=product_query,
                        conversation_id=conversation.id,
                        db=db
                    )
                    if order_result.get("success"):
                        # Replace generic LLM confirmation with detailed order receipt
                        ai_response_text = order_result["response"]
                        logger.info(f"🛒 Chat-confirmed order saved: {order_result.get('order', {}).get('order_id')} "
                                    f"(customer: {extracted_name}, email: {extracted_email}, product: {product_query})")
                    else:
                        logger.info(f"ℹ️ Chat order detection skipped: {order_result.get('response', 'no match')}")
                elif product_query:
                    logger.info(f"ℹ️ Order already placed via intent (ID: {existing_order_id})")
                else:
                    logger.warning(f"⚠️ Order confirmation detected but no product could be extracted from conversation")
        except Exception as chat_order_err:
            logger.warning(f"Chat order detection failed (non-blocking): {chat_order_err}")

    # ══════════════════════════════════════════════════════════════
    # Step 7: Behavioral Prediction (FR-5.4 — background)
    # Computes churn risk, purchase intent, escalation probability
    # ══════════════════════════════════════════════════════════════
    try:
        from app.services.prediction import get_predictor
        predictor = get_predictor()
        prediction = predictor.predict_escalation_probability(
            current_sentiment=customer_msg.sentiment or "neutral",
            sentiment_score=customer_msg.sentiment_score or 0.5,
            message_count=conversation.message_count or 1,
            has_urgent_keywords=sentiment_result.get("is_urgent", False),
            is_shouting=sentiment_result.get("is_shouting", False),
        )
        logger.info(
            f"Prediction: session={data.session_id} "
            f"escalation_prob={prediction.get('escalation_probability', 'N/A')} "
            f"will_escalate={prediction.get('will_escalate', False)}"
        )
    except Exception as e:
        logger.debug(f"Behavioral prediction skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # Step 8: Save AI response
    # ══════════════════════════════════════════════════════════════
    bot_name = "AI Assistant"
    try:
        widget_config = db.query(WidgetConfig).filter(
            WidgetConfig.tenant_id == tenant.id
        ).first()
        if widget_config:
            bot_name = widget_config.bot_name or "AI Assistant"
    except Exception:
        pass

    if ai_response_text:
        # Analyze AI response sentiment (not hardcoded)
        ai_sentiment = "positive"
        ai_sentiment_score = 0.7
        ai_sentiment_label = "Pleased"
        try:
            from app.services.sentiment import analyze_sentiment, get_sentiment_label
            ai_analysis = analyze_sentiment(ai_response_text, detected_lang if 'detected_lang' in dir() else 'en')
            ai_sentiment = ai_analysis.get("sentiment", "positive")
            ai_sentiment_score = ai_analysis.get("score", 0.7)
            ai_sentiment_label = ai_analysis.get("label", get_sentiment_label(ai_sentiment, ai_sentiment_score))
        except Exception:
            pass

        ai_msg = Message(
            tenant_id=tenant.id,
            conversation_id=conversation.id,
            content=ai_response_text,
            sender_type=MessageSender.AI.value,
            sender_name=bot_name,
            sentiment=ai_sentiment,
            sentiment_score=ai_sentiment_score,
            sentiment_label=ai_sentiment_label,
        )
        db.add(ai_msg)
        conversation.message_count = (conversation.message_count or 0) + 1
        conversation.updated_at = datetime.utcnow()
        db.commit()

    # ══════════════════════════════════════════════════════════════
    # Step 9: WebSocket push on escalation (FR-5.3.11)
    # Notifies the tenant's dashboard in real-time
    # ══════════════════════════════════════════════════════════════
    if should_escalate:
        try:
            from app.websocket.manager import get_manager
            ws_manager = get_manager()

            # Build handoff package (FR-5.3.10)
            handoff_package = {
                "type": "escalation_alert",
                "conversation_id": conversation.id,
                "session_id": conversation.session_id,
                "customer_name": conversation.customer_name or "Anonymous",
                "customer_email": conversation.customer_email,
                "priority": conversation.priority,
                "trigger_reasons": escalation_info.get("reasons", []),
                "sentiment_score": round(customer_msg.sentiment_score, 3),
                "frustration_level": round(conversation.frustration_level, 3),
                "message_count": conversation.message_count,
                "last_message": data.message[:200],
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Broadcast to tenant's dashboard room
            room_id = f"tenant_{tenant.id}"
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        ws_manager.broadcast_to_room(room_id, handoff_package)
                    )
                else:
                    loop.run_until_complete(
                        ws_manager.broadcast_to_room(room_id, handoff_package)
                    )
            except RuntimeError:
                asyncio.ensure_future(
                    ws_manager.broadcast_to_room(room_id, handoff_package)
                )

            logger.info(f"Escalation notification sent to room {room_id}")
        except Exception as e:
            logger.warning(f"WebSocket escalation push failed: {e}")

    # ══════════════════════════════════════════════════════════════
    # Response — matches what embed.js expects
    # embed.js reads: response.response (string), response.is_escalated, response.is_human_agent
    # ══════════════════════════════════════════════════════════════
    return {
        "response": ai_response_text,
        "is_escalated": should_escalate,
        "is_human_agent": is_human_takeover,
        "sentiment": {
            "score": round(customer_msg.sentiment_score, 3),
            "label": customer_msg.sentiment,
            "emotion": customer_msg.sentiment_label,
        },
        "confidence": round(confidence, 2),
    }


# ═══════════════════════════════════════════════════════════════════
# GET CHAT HISTORY (FR-6.2.14 — Session Persistence)
# embed.js calls: /api/widget/{key}/history?session_id=xxx
# ═══════════════════════════════════════════════════════════════════

@router.get("/{api_key}/history")
async def get_chat_history(
    api_key: str,
    session_id: str = Query(..., description="Session ID from localStorage"),
    db: Session = Depends(get_db)
):
    """
    Reload conversation history when customer refreshes page.
    Session ID stored in embed.js localStorage enables persistence.

    embed.js reads: data.messages[] with fields:
        .content, .sender_type, .sender_name, .created_at
    """
    tenant = get_tenant_by_api_key(api_key, db)

    conversation = db.query(Conversation).filter(
        Conversation.session_id == session_id,
        Conversation.tenant_id == tenant.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()

    return {
        "session_id": session_id,
        "conversation_id": conversation.id,
        "status": conversation.status,
        "messages": [
            {
                "content": msg.content,
                # ── embed.js uses sender_type for CSS class: .bai-msg.customer / .bai-msg.ai ──
                "sender_type": msg.sender_type,
                "sender_name": msg.sender_name,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]
    }
