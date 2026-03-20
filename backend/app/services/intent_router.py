"""
Intent-Based Query Router — V5 (Zone 5)
Classifies user messages and routes to the most efficient handler.

Classification Table:
  ORDER_QUERY   → SQL Lookup (bypasses RAG + LLM)
  ORDER_VERIFY  → Verify Engine (bypasses RAG + LLM)
  PURCHASE      → Order placement from widget (bypasses LLM) ★ V5 NEW
  PRODUCT_INFO  → RAG filtered to products → LLM
  COMPLAINT     → RAG → LLM + Escalation Check
  HUMAN_REQUEST → Direct Escalation (bypasses LLM)
  GENERAL_CHAT  → Full RAG → LLM (default)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Intent Categories
# ═══════════════════════════════════════════
INTENT_ORDER_QUERY = "ORDER_QUERY"
INTENT_ORDER_VERIFY = "ORDER_VERIFY"
INTENT_PURCHASE = "PURCHASE"          # ★ V5 NEW — Widget ordering
INTENT_PRODUCT_INFO = "PRODUCT_INFO"
INTENT_COMPLAINT = "COMPLAINT"
INTENT_HUMAN_REQUEST = "HUMAN_REQUEST"
INTENT_GENERAL_CHAT = "GENERAL_CHAT"

# ═══════════════════════════════════════════
# Pattern Matching
# ═══════════════════════════════════════════

# Order ID pattern: #ORD-12345, ORD12345, #12345, order 12345
ORDER_ID_PATTERN = re.compile(
    r'#?[A-Za-z]*-?\d{4,}',
    re.IGNORECASE
)

# ═══════════════════════════════════════════
# Keyword Sets (Multilingual)
# ═══════════════════════════════════════════

ORDER_KEYWORDS = {
    "order", "tracking", "status", "shipped", "delivered", "delivery",
    "where is my", "track my", "order number", "shipment", "shipping",
    "dispatch", "dispatched", "package", "parcel", "courier",
    "estimated delivery", "delivery date", "fedex", "ups", "dhl", "tcs",
    # Spanish
    "pedido", "envío",
    # French
    "commande", "livraison",
    # German
    "bestellung", "lieferung",
    # Urdu
    "آرڈر", "ڈیلیوری",
    # Hindi
    "ऑर्डर", "डिलीवरी",
}

VERIFY_KEYWORDS = {
    "verify order", "confirm my order", "verify my", "order verification",
    "check order", "validate order", "order id",
}

# ★ V5 NEW: Purchase intent keywords
PURCHASE_KEYWORDS = {
    "i want to buy", "i want to order", "place order", "place an order",
    "add to cart", "i'll take", "i will take", "order this", "buy this",
    "purchase this", "i'd like to order", "i would like to order",
    "can i order", "can i buy", "how do i order", "how to order",
    "i need to order", "want to purchase", "checkout", "book this",
    "buy it", "get this", "i'll order",
    # Spanish
    "quiero comprar", "ordenar", "comprar esto",
    # French
    "je veux acheter", "commander", "acheter",
    # German
    "ich möchte kaufen", "bestellen", "kaufen",
    # Urdu
    "خریدنا", "آرڈر کرنا",
    # Hindi
    "खरीदना", "ऑर्डर करना",
}

PRODUCT_KEYWORDS = {
    "price", "cost", "stock", "available", "product", "how much",
    "in stock", "out of stock", "catalog", "inventory",
    "item", "pricing", "show me", "tell me about",
    # Spanish
    "precio", "producto",
    # French
    "prix", "produit",
    # German
    "preis", "produkt",
    # Urdu
    "قیمت", "پروڈکٹ",
}

COMPLAINT_KEYWORDS = {
    "refund", "terrible", "broken", "damaged", "worst",
    "complaint", "complain", "awful", "horrible", "unacceptable",
    "disgusting", "ruined", "defective", "faulty",
}

HUMAN_KEYWORDS = {
    "human", "real person", "agent", "manager", "talk to someone",
    "speak to", "real human", "actual person", "customer service",
    "representative", "supervisor", "operator",
}

# General knowledge base keywords to explicitly route to RAG
KB_KEYWORDS = {
    "policy", "rules", "contact", "email", "phone", "address",
    "hours", "location", "terms", "conditions", "refund policy",
    "return policy", "shipping policy", "about", "who we are",
    "company", "support", "help", "guide", "faq", "frequently asked",
    # Spanish
    "política", "contacto", "términos",
    # French
    "politique", "contact", "conditions",
    # German
    "richtlinie", "kontakt",
}


# ═══════════════════════════════════════════
# Widget Type → Allowed Intents
# ═══════════════════════════════════════════
WIDGET_INTENT_MAP = {
    "full":   {INTENT_ORDER_QUERY, INTENT_ORDER_VERIFY, INTENT_PURCHASE,
               INTENT_PRODUCT_INFO, INTENT_COMPLAINT, INTENT_HUMAN_REQUEST,
               INTENT_GENERAL_CHAT},
    "info":   {INTENT_GENERAL_CHAT, INTENT_PRODUCT_INFO},
    "order":  {INTENT_ORDER_QUERY, INTENT_ORDER_VERIFY, INTENT_PURCHASE,
               INTENT_COMPLAINT, INTENT_HUMAN_REQUEST},
    "verify": {INTENT_ORDER_VERIFY},
}


def classify_intent(text: str, widget_type: str = "full",
                     sentiment: Optional[str] = None) -> dict:
    """
    Classify user message intent.

    Args:
        text: User message text
        widget_type: Widget type constraint (full/info/order/verify)
        sentiment: Detected sentiment (for complaint detection)

    Returns:
        dict with intent, confidence, extracted_data (e.g., order_id), reason
    """
    text_lower = text.lower().strip()
    allowed_intents = WIDGET_INTENT_MAP.get(widget_type, WIDGET_INTENT_MAP["full"])

    extracted_order_id = None
    intent = INTENT_GENERAL_CHAT
    confidence = 0.5

    # ── Priority 1: Human request (highest priority) ──
    human_matches = sum(1 for kw in HUMAN_KEYWORDS if kw in text_lower)
    if human_matches > 0 and INTENT_HUMAN_REQUEST in allowed_intents:
        return {
            "intent": INTENT_HUMAN_REQUEST,
            "confidence": min(0.6 + human_matches * 0.15, 0.95),
            "extracted_data": {},
            "reason": f"Human request keywords matched: {human_matches}"
        }

    # ── Priority 2: Order query (regex + keywords) ──
    # 0. Check for explicit Knowledge Base queries first
    # If a user explicitly asks about policies or general info, 
    # we MUST use RAG so we route to GENERAL_CHAT / PRODUCT_INFO.
    kb_matches = sum(1 for kw in KB_KEYWORDS if kw in text_lower)
    if kb_matches > 0:
        return {
            "intent": INTENT_GENERAL_CHAT,
            "confidence": 0.90,
            "extracted_data": {},
            "reason": f"Matched KB keywords (count: {kb_matches})"
        }

    # 1. Check for Explicit Order ID (Highest Priority if constraints allow)
    order_id_match = ORDER_ID_PATTERN.search(text_lower)
    if order_id_match and INTENT_ORDER_QUERY in allowed_intents:
        order_id = order_id_match.group(0).upper().lstrip('#')
        return {
            "intent": INTENT_ORDER_QUERY,
            "confidence": 0.95,
            "extracted_data": {"order_id": order_id},
            "reason": f"Found explicit order ID: {order_id}"
        }

    # Count keyword matches for other intents
    order_matches = sum(1 for kw in ORDER_KEYWORDS if kw in text_lower)
    verify_matches = sum(1 for kw in VERIFY_KEYWORDS if kw in text_lower)
    purchase_matches = sum(1 for kw in PURCHASE_KEYWORDS if kw in text_lower)
    complaint_matches = sum(1 for kw in COMPLAINT_KEYWORDS if kw in text_lower)
    product_matches = sum(1 for kw in PRODUCT_KEYWORDS if kw in text_lower)
    # human_matches is already calculated above

    # ── Priority 3: Order verification ──
    if verify_matches > 0 and INTENT_ORDER_VERIFY in allowed_intents:
        return {
            "intent": INTENT_ORDER_VERIFY,
            "confidence": min(0.6 + verify_matches * 0.15, 0.90),
            "extracted_data": {},
            "reason": f"Verify keywords matched: {verify_matches}"
        }

    # ── Priority 4: Purchase (★ V5 NEW — widget ordering) ──
    purchase_matches = sum(1 for kw in PURCHASE_KEYWORDS if kw in text_lower)
    if purchase_matches > 0 and INTENT_PURCHASE in allowed_intents:
        # Extract product query: remove purchase keywords to get the product part
        product_query = text_lower
        for kw in PURCHASE_KEYWORDS:
            product_query = product_query.replace(kw, "").strip()
        # Clean up leftover articles/prepositions
        for filler in ["the ", "a ", "an ", "some ", "this ", "that ", "those "]:
            if product_query.startswith(filler):
                product_query = product_query[len(filler):]
        product_query = product_query.strip(" .,!?")
        return {
            "intent": INTENT_PURCHASE,
            "confidence": min(0.6 + purchase_matches * 0.15, 0.95),
            "extracted_data": {"product_query": product_query if product_query else text_lower},
            "reason": f"Purchase keywords: {purchase_matches}"
        }

    # ── Priority 5: Complaint (negative sentiment + keywords) ──
    complaint_matches = sum(1 for kw in COMPLAINT_KEYWORDS if kw in text_lower)
    if (complaint_matches > 0 or sentiment == "negative") and INTENT_COMPLAINT in allowed_intents:
        if complaint_matches > 0:
            return {
                "intent": INTENT_COMPLAINT,
                "confidence": min(0.6 + complaint_matches * 0.1, 0.85),
                "extracted_data": {},
                "reason": f"Complaint keywords: {complaint_matches}"
            }

    # ── Priority 6: Product info ──
    product_matches = sum(1 for kw in PRODUCT_KEYWORDS if kw in text_lower)
    if product_matches >= 1 and INTENT_PRODUCT_INFO in allowed_intents:
        return {
            "intent": INTENT_PRODUCT_INFO,
            "confidence": min(0.5 + product_matches * 0.15, 0.85),
            "extracted_data": {},
            "reason": f"Product keywords: {product_matches}"
        }

    # ── Default: General chat ──
    if INTENT_GENERAL_CHAT not in allowed_intents:
        # Widget doesn't allow general chat — redirect to primary intent
        if widget_type == "order":
            intent = INTENT_ORDER_QUERY
        elif widget_type == "verify":
            intent = INTENT_ORDER_VERIFY
        else:
            intent = list(allowed_intents)[0] if allowed_intents else INTENT_GENERAL_CHAT

    return {
        "intent": intent,
        "confidence": confidence,
        "extracted_data": {},
        "reason": "Default classification"
    }


def extract_order_id(text: str) -> Optional[str]:
    """Extract order ID from text using regex."""
    match = ORDER_ID_PATTERN.search(text)
    if match:
        return match.group().lstrip('#')
    return None
