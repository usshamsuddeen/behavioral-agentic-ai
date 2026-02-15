"""
Conversations API — Zone 3: Chat Interface & Live Monitor
FRD v3.0 (FR-3.2)

All endpoints are tenant-scoped via JWT authentication.
Includes: list, get, human takeover, agent respond, escalate.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message, MessageSender
from app.middleware.jwt import get_current_user, get_tenant_for_user
from app.websocket.manager import get_manager

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class AgentResponseRequest(BaseModel):
    """FR-3.2.6: Agent typing a response to the customer"""
    message: str


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


def conversation_to_dict(conv: Conversation, db: Session) -> dict:
    """Convert a Conversation ORM object to an API response dict"""
    customer = None
    if conv.customer_id:
        customer = db.query(User).filter(User.id == conv.customer_id).first()
    
    return {
        "id": conv.id,
        "session_id": conv.session_id,
        "customer_id": conv.customer_id,
        "customer_name": conv.customer_name or (customer.name if customer else "Unknown"),
        "customer_email": conv.customer_email or (customer.email if customer else ""),
        "customer_avatar": customer.avatar_initials if customer else "U",
        "status": conv.status,
        "priority": conv.priority,
        "current_sentiment": conv.current_sentiment,
        "sentiment_score": conv.sentiment_score,
        "frustration_level": conv.frustration_level,
        "sentiment_emoji": get_sentiment_emoji(conv.current_sentiment, conv.sentiment_score or 0.5),
        "is_escalated": conv.is_escalated,
        "escalation_reason": conv.escalation_reason,
        "assigned_agent_id": conv.assigned_agent_id,
        "detected_language": conv.detected_language,
        "language_name": conv.language_name,
        "language_flag": conv.language_flag,
        "last_message_preview": conv.last_message_preview,
        "message_count": conv.message_count,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "escalated_at": conv.escalated_at.isoformat() if conv.escalated_at else None,
        "time_ago": get_time_ago(conv.updated_at)
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.2.1: Conversation List (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.get("/conversations")
async def list_conversations(
    status: Optional[str] = Query(None, description="Filter by status: active, escalated, resolved, closed"),
    search: Optional[str] = Query(None, description="Search by customer name or email"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.2.1: List all conversations for this tenant with status badges"""
    tenant = get_tenant_for_user(current_user, db)
    
    query = db.query(Conversation)
    
    # Tenant scoping — FR-7.3
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    # Status filter
    if status:
        query = query.filter(Conversation.status == status)
    
    # Search filter — FR-3.2.10
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Conversation.customer_name.ilike(search_term)) |
            (Conversation.customer_email.ilike(search_term))
        )
    
    conversations = query.order_by(Conversation.updated_at.desc()).limit(limit).all()
    
    return {
        "total": len(conversations),
        "conversations": [conversation_to_dict(conv, db) for conv in conversations]
    }


# ═══════════════════════════════════════════════════════════════════
# Conversation Detail with Messages
# ═══════════════════════════════════════════════════════════════════

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single conversation with all messages (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conv = query.first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    result = conversation_to_dict(conv, db)
    result["messages"] = [
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
    
    return result


# ═══════════════════════════════════════════════════════════════════
# Create Conversation (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.post("/conversations")
async def create_conversation(
    customer_name: str = "Unknown",
    customer_email: str = "",
    language: str = "en",
    language_name: str = "English",
    language_flag: str = "🇺🇸",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    
    conversation = Conversation(
        tenant_id=tenant.id if tenant else None,
        customer_name=customer_name,
        customer_email=customer_email,
        detected_language=language,
        language_name=language_name,
        language_flag=language_flag,
        session_id=Conversation.generate_session_id()
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return {
        "id": conversation.id,
        "session_id": conversation.session_id,
        "status": conversation.status,
        "message": "Conversation created successfully"
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.2.5: Human Takeover Button
# ═══════════════════════════════════════════════════════════════════

@router.post("/conversations/{conversation_id}/takeover")
async def takeover_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    FR-3.2.5: CLIENT agent clicks to take over from AI.
    Assigns the current user as the agent and marks the conversation for human handling.
    """
    tenant = get_tenant_for_user(current_user, db)
    
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conv = query.first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Assign agent and update status
    conv.assigned_agent_id = current_user.id
    conv.status = "active"  # Keep active, now human-handled
    
    # Add system message
    system_msg = Message(
        conversation_id=conv.id,
        tenant_id=conv.tenant_id,
        content=f"{current_user.get_display_name()} has taken over this conversation.",
        sender_type=MessageSender.SYSTEM.value,
        sender_name="System"
    )
    db.add(system_msg)
    conv.message_count = (conv.message_count or 0) + 1
    conv.updated_at = datetime.utcnow()
    db.commit()
    
    # Notify via WebSocket — FR-3.2.7
    try:
        manager = get_manager()
        await manager.broadcast_to_room(
            f"conversation_{conversation_id}",
            {
                "type": "agent_takeover",
                "conversation_id": conversation_id,
                "agent_name": current_user.get_display_name(),
                "message": f"{current_user.get_display_name()} has joined the conversation."
            }
        )
    except Exception:
        pass  # WebSocket notification is best-effort
    
    return {
        "id": conv.id,
        "assigned_agent_id": current_user.id,
        "agent_name": current_user.get_display_name(),
        "status": conv.status,
        "message": "Successfully taken over conversation"
    }


# ═══════════════════════════════════════════════════════════════════
# FR-3.2.6–FR-3.2.7: Agent Response
# ═══════════════════════════════════════════════════════════════════

@router.post("/conversations/{conversation_id}/respond")
async def agent_respond(
    conversation_id: int,
    data: AgentResponseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    FR-3.2.6: Agent types a response.
    FR-3.2.7: Response sent via WebSocket to the customer widget.
    """
    tenant = get_tenant_for_user(current_user, db)
    
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conv = query.first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create the agent message
    agent_msg = Message(
        conversation_id=conv.id,
        tenant_id=conv.tenant_id,
        content=data.message,
        sender_type=MessageSender.AGENT.value,
        sender_name=current_user.get_display_name(),
        sentiment="neutral",
        sentiment_score=0.5
    )
    db.add(agent_msg)
    
    # Update conversation
    conv.last_message_preview = data.message[:200]
    conv.message_count = (conv.message_count or 0) + 1
    conv.updated_at = datetime.utcnow()
    
    # If conversation was escalated, keep it active with agent
    if conv.is_escalated and not conv.assigned_agent_id:
        conv.assigned_agent_id = current_user.id
    
    db.commit()
    db.refresh(agent_msg)
    
    # Push to widget via WebSocket — FR-3.2.7
    try:
        manager = get_manager()
        await manager.broadcast_to_room(
            f"conversation_{conversation_id}",
            {
                "type": "agent_message",
                "conversation_id": conversation_id,
                "message": {
                    "id": agent_msg.id,
                    "content": data.message,
                    "sender_type": "agent",
                    "sender_name": current_user.get_display_name(),
                    "created_at": agent_msg.created_at.isoformat() if agent_msg.created_at else None
                }
            }
        )
    except Exception:
        pass  # WebSocket is best-effort
    
    return {
        "id": agent_msg.id,
        "conversation_id": conv.id,
        "content": data.message,
        "sender_type": "agent",
        "sender_name": current_user.get_display_name(),
        "created_at": agent_msg.created_at.isoformat() if agent_msg.created_at else None,
        "message": "Response sent successfully"
    }


# ═══════════════════════════════════════════════════════════════════
# Escalate Conversation (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.put("/conversations/{conversation_id}/escalate")
async def escalate_conversation(
    conversation_id: int,
    reason: str = "Manual escalation",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Escalate a conversation (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conv = query.first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.is_escalated = True
    conv.escalation_reason = reason
    conv.escalated_at = datetime.utcnow()
    conv.status = "escalated"
    conv.priority = "urgent"
    
    db.commit()
    
    # Notify via WebSocket
    try:
        manager = get_manager()
        await manager.broadcast_to_room(
            f"tenant_{conv.tenant_id}",
            {
                "type": "escalation_alert",
                "conversation_id": conv.id,
                "priority": "urgent",
                "reason": reason,
                "customer_name": conv.customer_name or "Unknown"
            }
        )
    except Exception:
        pass
    
    return {
        "id": conv.id,
        "is_escalated": True,
        "escalation_reason": reason,
        "priority": "urgent",
        "message": "Conversation escalated successfully"
    }


# ═══════════════════════════════════════════════════════════════════
# Resolve Conversation
# ═══════════════════════════════════════════════════════════════════

@router.put("/conversations/{conversation_id}/resolve")
async def resolve_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve a conversation (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if tenant:
        query = query.filter(Conversation.tenant_id == tenant.id)
    
    conv = query.first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.status = "resolved"
    conv.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": conv.id,
        "status": "resolved",
        "message": "Conversation resolved successfully"
    }
