"""
Messages API — Send and retrieve messages
FRD v3.0 — Tenant-scoped with JWT authentication

All message endpoints verify tenant ownership.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.message import Message, MessageSender
from app.models.conversation import Conversation
from app.models.user import User
from app.middleware.jwt import get_current_user, get_tenant_for_user
from app.services.sentiment import analyze_sentiment
from app.services.language import detect_language
from app.services.response_generator import get_response_generator

router = APIRouter()

# Escalation threshold (can be configured in settings)
ESCALATION_THRESHOLD = 0.85
AI_AUTO_REPLY_ENABLED = True


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class SendMessageRequest(BaseModel):
    content: str
    sender_type: str = "customer"
    sender_name: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def get_time_ago(dt: datetime) -> str:
    """Convert datetime to human readable time ago"""
    if not dt:
        return "Unknown"
    now = datetime.utcnow()
    diff = now - dt
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() // 60)
        return f"{mins}m"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() // 3600)
        return f"{hours}h"
    else:
        days = diff.days
        return f"{days}d"


def get_sentiment_emoji(sentiment: str, score: float) -> str:
    """Get emoji for sentiment"""
    if sentiment == "positive":
        return "😊" if score > 0.8 else "🙂"
    elif sentiment == "negative":
        if score < 0.2:
            return "😡"
        elif score < 0.4:
            return "😤"
        else:
            return "😟"
    return "😐"


# ═══════════════════════════════════════════════════════════════════
# SEND MESSAGE (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a new message and analyze sentiment.
    Tenant-scoped — verifies conversation belongs to user's tenant.
    """
    tenant = get_tenant_for_user(current_user, db)
    
    # Verify conversation belongs to this tenant
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conversation = query.first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    content = data.content
    sender_type = data.sender_type
    sender_name = data.sender_name or current_user.get_display_name()
    
    # 1. Detect language
    try:
        lang_result = detect_language(content)
        detected_lang = lang_result.get("language_code", "en")
    except Exception:
        detected_lang = "en"
    
    # 2. Analyze sentiment using the tiered system — FRD FR-5.2
    sentiment = "neutral"
    sentiment_score = 0.5
    sentiment_label = "Neutral"
    is_trigger = False
    trigger_keywords = None
    
    try:
        analysis = analyze_sentiment(content, detected_lang)
        sentiment = analysis.get("sentiment", "neutral")
        sentiment_score = analysis.get("score", 0.5)
        sentiment_label = analysis.get("label", "Neutral")
    except Exception as e:
        # Graceful degradation — use defaults
        pass
    
    # 3. Check for escalation keywords
    escalation_keywords = [
        "manager", "supervisor", "lawyer", "sue", "refund", "complaint",
        "report", "legal", "unacceptable", "disgusting", "worst"
    ]
    found_keywords = [kw for kw in escalation_keywords if kw in content.lower()]
    if found_keywords:
        is_trigger = True
        trigger_keywords = ",".join(found_keywords)
    
    # 4. Save the message
    message = Message(
        conversation_id=conversation_id,
        tenant_id=tenant.id if tenant else None,
        content=content,
        sender_type=sender_type,
        sender_name=sender_name,
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label,
        detected_language=detected_lang,
        is_escalation_trigger=is_trigger,
        trigger_keywords=trigger_keywords
    )
    db.add(message)
    
    # 5. Update conversation
    conversation.last_message_preview = content[:200]
    conversation.message_count = (conversation.message_count or 0) + 1
    conversation.current_sentiment = sentiment
    conversation.sentiment_score = sentiment_score
    conversation.updated_at = datetime.utcnow()
    
    # 6. Check escalation criteria — FRD FR-5.3
    should_escalate = False
    escalation_reason = None
    
    if sentiment == "negative" and sentiment_score < 0.25:
        should_escalate = True
        escalation_reason = "Critical negative sentiment (score < 0.25)"
    elif is_trigger:
        should_escalate = True
        escalation_reason = f"Escalation keywords detected: {', '.join(found_keywords)}"
    elif conversation.frustration_level and conversation.frustration_level >= ESCALATION_THRESHOLD:
        should_escalate = True
        escalation_reason = f"Frustration level exceeded threshold ({conversation.frustration_level:.0%})"
    
    if should_escalate and not conversation.is_escalated:
        conversation.is_escalated = True
        conversation.escalation_reason = escalation_reason
        conversation.escalated_at = datetime.utcnow()
        conversation.status = "escalated"
        conversation.priority = "urgent"
    
    # Increment frustration level on negative sentiment
    if sentiment == "negative":
        current_frustration = conversation.frustration_level or 0.0
        conversation.frustration_level = min(current_frustration + 0.15, 1.0)
    elif sentiment == "positive":
        current_frustration = conversation.frustration_level or 0.0
        conversation.frustration_level = max(current_frustration - 0.1, 0.0)
    
    db.commit()
    db.refresh(message)
    
    # 7. Generate AI auto-reply if:
    #    - Sender is customer
    #    - AI auto-reply is enabled
    #    - Conversation is NOT currently assigned to an agent
    ai_response = None
    if (
        sender_type == "customer"
        and AI_AUTO_REPLY_ENABLED
        and not conversation.assigned_agent_id
        and not should_escalate
    ):
        try:
            generator = get_response_generator()
            ai_reply_text = await generator.generate(
                query=content,
                tenant_id=str(tenant.id) if tenant else "default",
                conversation_history=[],
                language=detected_lang
            )
            
            if ai_reply_text:
                ai_msg = Message(
                    conversation_id=conversation_id,
                    tenant_id=tenant.id if tenant else None,
                    content=ai_reply_text,
                    sender_type=MessageSender.AI.value,
                    sender_name="AI Assistant",
                    sentiment="neutral",
                    sentiment_score=0.5,
                    detected_language=detected_lang
                )
                db.add(ai_msg)
                conversation.message_count = (conversation.message_count or 0) + 1
                conversation.last_message_preview = ai_reply_text[:200]
                db.commit()
                db.refresh(ai_msg)
                
                ai_response = {
                    "id": ai_msg.id,
                    "content": ai_reply_text,
                    "sender_type": "ai",
                    "sender_name": "AI Assistant",
                    "created_at": ai_msg.created_at.isoformat() if ai_msg.created_at else None
                }
        except Exception:
            pass  # AI response generation is best-effort
    
    result = {
        "id": message.id,
        "conversation_id": conversation_id,
        "content": content,
        "sender_type": sender_type,
        "sender_name": sender_name,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "sentiment_emoji": get_sentiment_emoji(sentiment, sentiment_score),
        "is_escalation_trigger": is_trigger,
        "detected_language": detected_lang,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "escalation": {
            "triggered": should_escalate,
            "reason": escalation_reason
        } if should_escalate else None
    }
    
    if ai_response:
        result["ai_response"] = ai_response
    
    return result


# ═══════════════════════════════════════════════════════════════════
# GET MESSAGES (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.get("/api/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a conversation (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    
    # Verify conversation belongs to this tenant
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conversation = query.first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return {
        "conversation_id": conversation_id,
        "total": len(messages),
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "sender_type": msg.sender_type,
                "sender_name": msg.sender_name,
                "sentiment": msg.sentiment,
                "sentiment_score": msg.sentiment_score,
                "sentiment_label": msg.sentiment_label,
                "sentiment_emoji": get_sentiment_emoji(msg.sentiment or "neutral", msg.sentiment_score or 0.5),
                "is_escalation_trigger": msg.is_escalation_trigger,
                "detected_language": msg.detected_language,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "time_ago": get_time_ago(msg.created_at)
            }
            for msg in messages
        ]
    }
