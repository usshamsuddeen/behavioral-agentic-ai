"""
Escalation Service
Detects escalation triggers and recommends when to escalate conversations
"""

import re
from typing import Dict, List


from app.services.sentiment import SENTIMENT_DICTS, URGENT_KEYWORDS as GLOBAL_URGENT_KEYWORDS

# Build Multilingual Escalation Keywords from Sentiment Service
ESCALATION_KEYWORDS = set(GLOBAL_URGENT_KEYWORDS)

# Add language-specific urgent keywords
for lang, data in SENTIMENT_DICTS.items():
    if "urgent" in data:
        ESCALATION_KEYWORDS.update(data["urgent"])

# Add specific escalation phrases — ONLY genuine anger/threats.
# Normal e-commerce actions (cancel, refund, review) are NOT escalation triggers
# because customers saying "Can I cancel my order?" shouldn't be escalated.
ADDITIONAL_TRIGGERS = {
    # Human escalation requests (genuine)
    "speak to someone", "higher up", "your boss", "manager", "supervisor",
    "real person", "human agent", "talk to a human", "actual person",
    "someone in charge", "department manager", "customer service manager",
    
    # Strong dissatisfaction (genuine anger, not standard requests)
    "never again", "worst ever", "terrible service", "awful experience",
    "completely unacceptable", "absolutely terrible", "disgusted",
    "fed up", "had enough", "last straw", "final warning",
    
    # Legal/formal threats
    "consumer protection", "file a complaint", "report you",
    "legal action", "sue you", "better business bureau", "bbb",
    "trading standards", "consumer rights", "regulatory",
    
    # Frustration expressions
    "this is ridiculous", "how dare you",
    "are you kidding", "joke of a company",
}
ESCALATION_KEYWORDS.update(ADDITIONAL_TRIGGERS)

# Remove overly broad words that trigger on normal e-commerce messages
# These are standard customer actions, NOT escalation signals
FALSE_POSITIVE_WORDS = {
    "cancel", "refund", "review", "money back", "full refund",
    "want my money", "refund now", "compensation", "credit my account",
    "reimburse", "pay me back", "scam", "fraud", "rip off",
    "unbelievable", "what the", "asap", "right now", "immediately",
    "need this resolved", "urgent matter", "time sensitive", "emergency",
    "critical issue", "need immediate",
}
ESCALATION_KEYWORDS -= FALSE_POSITIVE_WORDS

# Caps lock indicates frustration
MIN_CAPS_RATIO = 0.4

# Repeated punctuation indicates strong emotion
REPEATED_PUNCTUATION_PATTERN = r'[!?]{2,}'


def check_escalation_triggers(text: str, current_frustration: float = 0.0) -> Dict:
    """
    Check if message contains escalation triggers.
    Returns trigger status, matched keywords, and escalation recommendation.

    Tuned to avoid false positives on short or ambiguous messages
    (e.g. "??", "ok", "hi") while still catching genuine frustration.
    """
    text_lower = text.lower().strip()
    text_stripped = text.strip()
    matched_keywords = []
    trigger_score = 0.0
    reasons = []

    # ── Guard: very short messages (< 5 chars) should never trigger escalation ──
    # Inputs like "??", "ok", "hi", "no" are too ambiguous to act on
    is_short_message = len(text_stripped) < 5

    # ── 1. Check for escalation keywords (highest signal) ──
    # Only check keyword matches on messages with actual words (>= 5 chars)
    if not is_short_message:
        for keyword in ESCALATION_KEYWORDS:
            if keyword in text_lower:
                matched_keywords.append(keyword)
                trigger_score += 0.20  # Moderate signal per keyword (was 0.30 — too aggressive)

        if matched_keywords:
            reasons.append(f"Escalation keywords: {', '.join(matched_keywords[:3])}")

    # ── 2. Check for caps lock usage (only meaningful on longer text) ──
    if len(text_stripped) > 15:
        alpha_chars = [c for c in text_stripped if c.isalpha()]
        if alpha_chars:
            caps_count = sum(1 for c in alpha_chars if c.isupper())
            caps_ratio = caps_count / len(alpha_chars)
            if caps_ratio > MIN_CAPS_RATIO:
                trigger_score += 0.20
                reasons.append("Excessive caps lock usage")

    # ── 3. Check for repeated punctuation ──
    # Only contributes a small amount — not enough to escalate alone
    if re.search(REPEATED_PUNCTUATION_PATTERN, text_stripped):
        if is_short_message:
            # "??" or "!!!" on its own = minor signal, NOT escalation-worthy
            trigger_score += 0.05
        else:
            # "THIS IS RIDICULOUS!!!" = moderate signal alongside other evidence
            trigger_score += 0.10
        reasons.append("Emotional punctuation detected")

    # ── 4. Factor in current frustration level ──
    if current_frustration > 0.7:
        trigger_score += 0.25
        reasons.append(f"High frustration level ({int(current_frustration * 100)}%)")
    elif current_frustration > 0.5:
        trigger_score += 0.15
        reasons.append(f"Elevated frustration ({int(current_frustration * 100)}%)")

    # ── 5. Determine escalation recommendation ──
    # is_trigger: signals that *something* was detected (for logging/UI)
    is_trigger = len(matched_keywords) > 0 or trigger_score > 0.35

    # should_escalate: requires STRONG evidence before routing to human
    # Raised from 0.45 → 0.60 to prevent false positives on normal messages.
    # A single keyword (0.20) is NOT enough — need multiple signals:
    #   - 3 keywords alone = 0.60 ✓
    #   - 2 keywords + high frustration = 0.40 + 0.25 = 0.65 ✓
    #   - 1 keyword + caps + punctuation = 0.20 + 0.20 + 0.10 = 0.50 ✗ (needs more)
    should_escalate = (
        trigger_score >= 0.60
        or (len(matched_keywords) > 0 and current_frustration > 0.70)
    )

    return {
        "is_trigger": is_trigger,
        "should_escalate": should_escalate,
        "trigger_score": round(min(trigger_score, 1.0), 2),
        "keywords": matched_keywords,
        "reasons": reasons,
        "reason": reasons[0] if reasons else "No specific trigger"
    }


def calculate_escalation_priority(
    sentiment_score: float,
    frustration_level: float,
    message_count: int,
    has_triggers: bool
) -> str:
    """
    Calculate escalation priority based on multiple factors.
    Returns: 'low', 'normal', 'high', or 'urgent'
    """
    priority_score = 0.0
    
    # Sentiment contribution (negative = higher priority)
    if sentiment_score < 0.3:
        priority_score += 0.4
    elif sentiment_score < 0.5:
        priority_score += 0.2
    
    # Frustration contribution
    priority_score += frustration_level * 0.3
    
    # Message count (more messages = more invested customer)
    if message_count > 10:
        priority_score += 0.15
    elif message_count > 5:
        priority_score += 0.1
    
    # Trigger presence
    if has_triggers:
        priority_score += 0.2
    
    # Map to priority level
    if priority_score >= 0.7:
        return "urgent"
    elif priority_score >= 0.5:
        return "high"
    elif priority_score >= 0.3:
        return "normal"
    else:
        return "low"
