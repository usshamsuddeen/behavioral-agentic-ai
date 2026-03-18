"""
Order Placement Service — V5 NEW
Handles widget-based order creation when customer wants to purchase.

Called by widget_api.py when intent_router classifies as INTENT_PURCHASE.
Flow: fuzzy product match → stock check → create order → auto-index RAG.

Author: Behavioral Agentic AI Team
Version: 5.0.0
"""

import logging
import json
import random
import string
from datetime import datetime, timedelta
from typing import Optional
from difflib import SequenceMatcher
from sqlalchemy.orm import Session

from app.models.order import CustomerOrder
from app.models.product_listing import ProductListing

logger = logging.getLogger(__name__)


def _generate_widget_order_id(tenant_id: int, db: Session) -> str:
    """Generate a unique widget order ID: WO-YYYYMMDD-XXXXX with collision check."""
    date_part = datetime.utcnow().strftime("%Y%m%d")
    for _ in range(10):  # max 10 attempts
        rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        order_id = f"WO-{date_part}-{rand_part}"
        exists = db.query(CustomerOrder.id).filter(
            CustomerOrder.tenant_id == tenant_id,
            CustomerOrder.order_id == order_id,
        ).first()
        if not exists:
            return order_id
    # Fallback: add extra randomness
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"WO-{date_part}-{rand_part}"


def _fuzzy_match_product(
    query: str,
    tenant_id: int,
    db: Session,
    threshold: float = 0.45,
) -> Optional[ProductListing]:
    """
    Find the best-matching product for a customer's text query.
    Uses name similarity + keyword containment.
    """
    if not query or not query.strip():
        return None

    query_lower = query.lower().strip()

    products = db.query(ProductListing).filter(
        ProductListing.tenant_id == tenant_id
    ).all()

    if not products:
        return None

    best_product = None
    best_score = 0.0

    for product in products:
        name_lower = product.name.lower()

        # Exact substring match is strongest signal
        if query_lower in name_lower or name_lower in query_lower:
            score = 0.95
        else:
            # SequenceMatcher ratio
            score = SequenceMatcher(None, query_lower, name_lower).ratio()

            # Boost if individual query words appear in product name
            query_words = query_lower.split()
            name_words = name_lower.split()
            word_hits = sum(1 for qw in query_words if any(qw in nw for nw in name_words))
            if query_words:
                word_boost = (word_hits / len(query_words)) * 0.3
                score = score * 0.7 + word_boost

        if score > best_score:
            best_score = score
            best_product = product

    if best_score >= threshold:
        logger.info(f"✅ Product match: '{query}' → '{best_product.name}' (score: {best_score:.2f})")
        return best_product

    logger.info(f"❌ No product match for '{query}' (best score: {best_score:.2f})")
    return None


def place_widget_order(
    tenant_id: int,
    customer_name: str,
    customer_email: str,
    product_query: str,
    conversation_id: int,
    db: Session,
) -> dict:
    """
    Place an order from the widget chat.

    Returns:
        dict with 'success', 'response' (AI text), and optionally 'order' data.
    """
    # Step 1: Find the product
    product = _fuzzy_match_product(product_query, tenant_id, db)

    if not product:
        return {
            "success": False,
            "response": (
                f"I wasn't able to find a product matching \"{product_query}\" in our catalog. "
                f"Could you please provide the exact product name or browse our products? "
                f"I'm happy to help you find what you're looking for! 😊"
            ),
        }

    # Step 2: Check stock
    if not product.in_stock or (product.stock_quantity is not None and product.stock_quantity <= 0):
        return {
            "success": False,
            "response": (
                f"I found **{product.name}** but unfortunately it's currently out of stock. "
                f"Would you like me to notify you when it's back, or can I help you find an alternative?"
            ),
        }

    # Step 3: Create the order
    order_id = _generate_widget_order_id(tenant_id, db)
    price = product.price or 0.0
    currency = product.currency or "USD"

    items_json = json.dumps([{
        "name": product.name,
        "qty": 1,
        "price": price,
        "sku": product.sku or "",
    }])

    order = CustomerOrder(
        tenant_id=tenant_id,
        order_id=order_id,
        customer_name=customer_name,
        customer_email=customer_email,
        status="confirmed",
        total_amount=price,
        currency=currency,
        items=items_json,
        order_date=datetime.utcnow(),
        estimated_delivery=datetime.utcnow() + timedelta(days=random.randint(3, 7)),
        notes=f"Widget order from conversation #{conversation_id}",
        source="widget",
    )
    db.add(order)

    # Step 4: Update stock (decrement by 1) — same transaction as order
    if product.stock_quantity is not None and product.stock_quantity > 0:
        product.stock_quantity -= 1
        if product.stock_quantity == 0:
            product.in_stock = False

    # Single atomic commit: order + stock update together
    db.commit()
    db.refresh(order)

    # Step 5: Auto-index to vector store for RAG (non-blocking)
    try:
        from app.api.orders_api import _auto_index_order
        _auto_index_order(order, tenant_id)
    except Exception as e:
        logger.warning(f"Widget order auto-index failed (non-blocking): {e}")

    # Step 6: Build confirmation response
    delivery_date = order.estimated_delivery.strftime("%B %d, %Y") if order.estimated_delivery else "3-7 business days"

    response = (
        f"✅ **Order Placed Successfully!**\n\n"
        f"📦 **Order ID:** #{order_id}\n"
        f"🛍️ **Product:** {product.name}\n"
        f"💰 **Total:** {currency} {price:.2f}\n"
        f"📅 **Estimated Delivery:** {delivery_date}\n\n"
        f"You'll receive updates about your order. Is there anything else I can help you with?"
    )

    logger.info(
        f"🛒 Widget order placed: {order_id} for tenant {tenant_id} "
        f"(product: {product.name}, amount: {currency} {price:.2f})"
    )

    return {
        "success": True,
        "response": response,
        "order": order.to_dict(),
    }
