"""
Widget API — Zone 6: Customer-Facing Chat Endpoints
FRD v3.0 (FR-6.1, FR-6.2)

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
    # Step 5: Generate AI Response via Agent (FR-5.2 + FR-5.3)
    # The AI agent internally handles:
    #   - RAG retrieval (knowledge base context)
    #   - LLM response generation
    #   - Escalation detection (keywords, sentiment, frustration)
    # This is the SINGLE source of truth for escalation decisions.
    # Previously, escalation was checked twice (here AND in agent.py)
    # which caused false triggers on normal messages.
    # ══════════════════════════════════════════════════════════════
    ai_response_text = "I'm here to help! Let me look into that for you."
    confidence = 0.5
    should_escalate = False
    escalation_info = {}

    if is_human_takeover:
        # Human agent has taken over — don't auto-respond with AI
        ai_response_text = None
    else:
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
                company_guidelines=tenant.description,
                current_frustration=conversation.frustration_level or 0.0,
                detected_language=detected_lang,
                pre_sentiment={
                    "sentiment": sentiment_result.get("sentiment", "neutral"),
                    "score": sentiment_result.get("score", 0.5),
                    "confidence": sentiment_result.get("confidence", 0.5),
                    "label": sentiment_result.get("label", "neutral"),
                    "is_urgent": sentiment_result.get("is_urgent", False),
                },
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
            logger.warning(f"AI agent failed, using fallback: {e}")

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
        ai_msg = Message(
            tenant_id=tenant.id,
            conversation_id=conversation.id,
            content=ai_response_text,
            sender_type=MessageSender.AI.value,
            sender_name=bot_name,
            sentiment="positive",
            sentiment_score=0.7,
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
