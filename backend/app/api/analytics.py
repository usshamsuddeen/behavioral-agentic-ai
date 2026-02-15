"""
Analytics API — Zone 3: Dashboard Metrics & Statistics
FRD v3.0 (FR-3.1, FR-3.3)

All endpoints are tenant-scoped via JWT authentication.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.models.tenant import Tenant
from app.models.widget_config import WidgetConfig
from app.middleware.jwt import get_current_user, get_tenant_for_user

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# FR-3.1: Dashboard Home Metrics (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.get("/api/dashboard/metrics")
async def get_dashboard_metrics(
    period: str = Query("week", description="Period: today, week, month"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    FR-3.1: Dashboard home metrics overview.
    Scoped to the authenticated user's tenant.
    Returns: conversation counts, sentiment distribution, escalation rate, widget status.
    """
    tenant = get_tenant_for_user(current_user, db)
    
    # If super_admin, show system-wide metrics
    if tenant is None:
        tenant_filter = True  # No filter — see all
    else:
        tenant_filter = Conversation.tenant_id == tenant.id
    
    # Period filter
    now = datetime.utcnow()
    if period == "today":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        period_start = now - timedelta(days=30)
    else:  # week (default)
        period_start = now - timedelta(days=7)
    
    period_filter = Conversation.created_at >= period_start
    
    # FR-3.1.1: Total conversations count
    total_conversations = db.query(func.count(Conversation.id)).filter(
        tenant_filter, period_filter
    ).scalar() or 0
    
    # FR-3.1.2: Active conversations count
    active_conversations = db.query(func.count(Conversation.id)).filter(
        tenant_filter,
        Conversation.status == "active"
    ).scalar() or 0
    
    # Escalated conversations
    escalated_conversations = db.query(func.count(Conversation.id)).filter(
        tenant_filter,
        Conversation.is_escalated == True,
        period_filter
    ).scalar() or 0
    
    # FR-3.1.3: Average sentiment score
    avg_sentiment = db.query(func.avg(Conversation.sentiment_score)).filter(
        tenant_filter, period_filter
    ).scalar()
    avg_sentiment = round(float(avg_sentiment), 2) if avg_sentiment else 0.5
    
    # FR-3.1.4: Escalation rate
    escalation_rate = round(
        (escalated_conversations / max(total_conversations, 1)) * 100, 1
    )
    
    # FR-3.1.5: Sentiment distribution
    positive_count = db.query(func.count(Conversation.id)).filter(
        tenant_filter, period_filter,
        Conversation.current_sentiment == "positive"
    ).scalar() or 0
    neutral_count = db.query(func.count(Conversation.id)).filter(
        tenant_filter, period_filter,
        Conversation.current_sentiment == "neutral"
    ).scalar() or 0
    negative_count = db.query(func.count(Conversation.id)).filter(
        tenant_filter, period_filter,
        Conversation.current_sentiment == "negative"
    ).scalar() or 0
    
    total_sentiment = positive_count + neutral_count + negative_count
    
    # Language distribution
    language_dist = db.query(
        Conversation.detected_language,
        Conversation.language_name,
        Conversation.language_flag,
        func.count(Conversation.id).label('count')
    ).filter(tenant_filter, period_filter).group_by(
        Conversation.detected_language,
        Conversation.language_name,
        Conversation.language_flag
    ).all()
    
    # FR-3.1.7: Recent escalations list (last 5)
    recent_escalations = db.query(Conversation).filter(
        tenant_filter,
        Conversation.is_escalated == True
    ).order_by(Conversation.escalated_at.desc()).limit(5).all()
    
    # FR-3.1.8: Widget status indicator
    widget_status = "inactive"
    if tenant:
        widget_config = db.query(WidgetConfig).filter(
            WidgetConfig.tenant_id == tenant.id
        ).first()
        widget_status = "active" if (widget_config and widget_config.is_active) else "inactive"
    
    # Satisfaction score (derived from positive sentiment ratio)
    satisfaction = round((positive_count / max(total_sentiment, 1)) * 100)
    
    return {
        "overview": {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "escalated_count": escalated_conversations,
            "avg_sentiment_score": avg_sentiment,
            "escalation_rate": escalation_rate,
            "satisfaction_score": satisfaction,
            "avg_response_time": "1.2s",
            "period": period
        },
        "sentiment_distribution": {
            "positive": positive_count,
            "neutral": neutral_count,
            "negative": negative_count,
            "positive_percent": round((positive_count / max(total_sentiment, 1)) * 100),
            "neutral_percent": round((neutral_count / max(total_sentiment, 1)) * 100),
            "negative_percent": round((negative_count / max(total_sentiment, 1)) * 100)
        },
        "language_distribution": [
            {
                "code": lang.detected_language,
                "name": lang.language_name,
                "flag": lang.language_flag,
                "count": lang.count,
                "percent": round((lang.count / max(total_conversations, 1)) * 100)
            }
            for lang in language_dist
        ],
        "recent_escalations": [
            {
                "id": esc.id,
                "customer_name": esc.customer_name or "Unknown",
                "priority": esc.priority,
                "escalation_reason": esc.escalation_reason,
                "status": esc.status,
                "escalated_at": esc.escalated_at.isoformat() if esc.escalated_at else None
            }
            for esc in recent_escalations
        ],
        "widget_status": widget_status
    }


# ═══════════════════════════════════════════════════════════════════
# LEGACY ENDPOINT (backwards-compatible, now tenant-scoped)
# ═══════════════════════════════════════════════════════════════════

@router.get("/analytics/dashboard")
async def get_dashboard_metrics_legacy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy endpoint — redirects to new tenant-scoped metrics"""
    return await get_dashboard_metrics(period="week", current_user=current_user, db=db)


# ═══════════════════════════════════════════════════════════════════
# FR-3.3.1: Sentiment Trends Chart
# ═══════════════════════════════════════════════════════════════════

@router.get("/analytics/sentiment-trends")
async def get_sentiment_trends(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.3.1: Sentiment trends over time (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    tenant_filter = Conversation.tenant_id == tenant.id if tenant else True
    
    trends = []
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=(days - 1 - i))
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_filter = and_(
            Conversation.created_at >= day_start,
            Conversation.created_at < day_end
        )
        
        positive = db.query(func.count(Conversation.id)).filter(
            tenant_filter, day_filter, Conversation.current_sentiment == "positive"
        ).scalar() or 0
        neutral = db.query(func.count(Conversation.id)).filter(
            tenant_filter, day_filter, Conversation.current_sentiment == "neutral"
        ).scalar() or 0
        negative = db.query(func.count(Conversation.id)).filter(
            tenant_filter, day_filter, Conversation.current_sentiment == "negative"
        ).scalar() or 0
        
        avg_score = db.query(func.avg(Conversation.sentiment_score)).filter(
            tenant_filter, day_filter
        ).scalar()
        
        trends.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": date.strftime("%a"),
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "avg_score": round(float(avg_score), 2) if avg_score else 0.5
        })
    
    return {"days": days, "trends": trends}


# ═══════════════════════════════════════════════════════════════════
# FR-3.3.6: Conversation Volume Heatmap
# ═══════════════════════════════════════════════════════════════════

@router.get("/analytics/hourly-activity")
async def get_hourly_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.3.6: Hourly/daily heatmap of conversation activity (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    tenant_filter = Conversation.tenant_id == tenant.id if tenant else True
    
    # Get actual data from last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    conversations = db.query(Conversation).filter(
        tenant_filter,
        Conversation.created_at >= week_ago
    ).all()
    
    # Build heatmap
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heatmap_data = {}
    for day in days:
        for hour in range(24):
            heatmap_data[(day, hour)] = 0
    
    for conv in conversations:
        if conv.created_at:
            day_name = conv.created_at.strftime("%a")
            hour = conv.created_at.hour
            if (day_name, hour) in heatmap_data:
                heatmap_data[(day_name, hour)] += 1
    
    max_count = max(heatmap_data.values()) if heatmap_data else 1
    
    heatmap = []
    for day in days:
        for hour in range(24):
            count = heatmap_data[(day, hour)]
            heatmap.append({
                "day": day,
                "hour": hour,
                "intensity": round(count / max(max_count, 1), 2),
                "count": count
            })
    
    return {"heatmap": heatmap}


# ═══════════════════════════════════════════════════════════════════
# FR-3.3.4: Top Escalation Reasons
# ═══════════════════════════════════════════════════════════════════

@router.get("/analytics/escalation-triggers")
async def get_escalation_triggers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """FR-3.3.4: Most common escalation trigger keywords (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    tenant_filter = Conversation.tenant_id == tenant.id if tenant else True
    
    # Get escalated conversations
    escalated = db.query(Conversation).filter(
        tenant_filter,
        Conversation.is_escalated == True
    ).all()
    
    total = len(escalated)
    
    # Count trigger reasons
    trigger_counts = {}
    for conv in escalated:
        if conv.escalation_reason:
            reasons = conv.escalation_reason.split(",")
            for reason in reasons:
                reason = reason.strip()
                trigger_counts[reason] = trigger_counts.get(reason, 0) + 1
    
    # Sort by count
    sorted_triggers = sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    triggers = [
        {
            "name": name,
            "count": count,
            "percent": round((count / max(total, 1)) * 100)
        }
        for name, count in sorted_triggers
    ]
    
    # If no real data, provide default categories
    if not triggers:
        triggers = [
            {"name": "Negative sentiment spike", "count": 0, "percent": 0},
            {"name": "Escalation keywords", "count": 0, "percent": 0},
            {"name": "Repeated negative messages", "count": 0, "percent": 0},
            {"name": "Human agent request", "count": 0, "percent": 0},
            {"name": "Caps lock frustration", "count": 0, "percent": 0},
        ]
    
    return {"total_escalations": total, "triggers": triggers}


# ═══════════════════════════════════════════════════════════════════
# Sentiment by Language (tenant-scoped)
# ═══════════════════════════════════════════════════════════════════

@router.get("/analytics/sentiment-by-language")
async def get_sentiment_by_language(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sentiment distribution broken down by language (tenant-scoped)"""
    tenant = get_tenant_for_user(current_user, db)
    tenant_filter = Conversation.tenant_id == tenant.id if tenant else True
    
    results = db.query(
        Conversation.detected_language,
        Conversation.language_flag,
        Conversation.current_sentiment,
        func.count(Conversation.id)
    ).filter(tenant_filter).group_by(
        Conversation.detected_language,
        Conversation.current_sentiment
    ).all()
    
    lang_data = {}
    for lang_code, flag, sentiment, count in results:
        if lang_code not in lang_data:
            lang_data[lang_code] = {
                "code": lang_code,
                "flag": flag,
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "total": 0
            }
        lang_data[lang_code][sentiment] = count
        lang_data[lang_code]["total"] += count
    
    formatted_data = []
    for code, data in lang_data.items():
        total = max(data["total"], 1)
        formatted_data.append({
            "code": code,
            "flag": data["flag"],
            "positive_pct": round((data["positive"] / total) * 100),
            "neutral_pct": round((data["neutral"] / total) * 100),
            "negative_pct": round((data["negative"] / total) * 100),
            "total_conversations": total
        })
    
    formatted_data.sort(key=lambda x: x["total_conversations"], reverse=True)
    return {"breakdown": formatted_data}
