"""
Order Query Engine — SQL Lookup for Order Queries
V4 NEW — Zone 8 (FR-8.3)

Called by the Intent Router when intent = ORDER_QUERY.
Performs direct SQL lookup — bypasses RAG + LLM for speed.
"""

import re
import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session

from app.models.order import CustomerOrder

logger = logging.getLogger(__name__)

# Order ID extraction pattern
ORDER_ID_PATTERN = re.compile(r'#?([A-Za-z]*-?\d{4,})')


def extract_order_id(text: str) -> Optional[str]:
    """Extract order ID from message text."""
    match = ORDER_ID_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def extract_email(text: str) -> Optional[str]:
    """Extract email address from message text."""
    email_pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
    match = email_pattern.search(text)
    if match:
        return match.group()
    return None


def lookup_order(
    order_id: Optional[str] = None,
    email: Optional[str] = None,
    tenant_id: int = 0,
    db: Session = None
) -> Dict:
    """
    Look up order by order_id or email.

    Returns:
        dict with "found" (bool), "order" (dict or None), "response" (str)
    """
    if not db:
        return {"found": False, "order": None, "response": "Database not available."}

    order = None

    # Priority 1: Lookup by order_id
    if order_id:
        # Try exact match and with/without '#' prefix
        order = db.query(CustomerOrder).filter(
            CustomerOrder.tenant_id == tenant_id,
            (CustomerOrder.order_id == order_id) |
            (CustomerOrder.order_id == f"#{order_id}") |
            (CustomerOrder.order_id == order_id.lstrip('#'))
        ).first()

    # Priority 2: Lookup by email (returns latest order)
    if not order and email:
        order = db.query(CustomerOrder).filter(
            CustomerOrder.tenant_id == tenant_id,
            CustomerOrder.customer_email == email
        ).order_by(CustomerOrder.order_date.desc()).first()

    # Format response
    if order:
        return {
            "found": True,
            "order": order.to_dict(),
            "response": _format_found_response(order)
        }
    else:
        return {
            "found": False,
            "order": None,
            "response": _format_not_found_response(order_id, email)
        }


def _format_found_response(order: CustomerOrder) -> str:
    """Format a found order into natural language response."""
    response = f"Here's the status of your order #{order.order_id}:\n\n"
    response += f"📦 **Status:** {order.status.title()}\n"

    if order.order_date:
        response += f"📅 **Order Date:** {order.order_date.strftime('%B %d, %Y')}\n"
    if order.total_amount:
        response += f"💰 **Total:** {order.currency} {order.total_amount:.2f}\n"

    if order.status == "shipped" and order.tracking_number:
        response += f"\n🚚 **Tracking Number:** {order.tracking_number}\n"
        if order.carrier:
            response += f"📮 **Carrier:** {order.carrier}\n"
        if order.estimated_delivery:
            response += f"📅 **Estimated Delivery:** {order.estimated_delivery.strftime('%B %d, %Y')}\n"
    elif order.status == "delivered":
        response += "\n✅ Your order has been delivered!"
        if order.estimated_delivery:
            response += f" (Delivered around {order.estimated_delivery.strftime('%B %d, %Y')})"
    elif order.status == "pending":
        response += "\n⏳ Your order is being processed. We'll update you once it ships."
    elif order.status == "cancelled":
        response += "\n❌ This order has been cancelled."
    elif order.status == "refunded":
        response += "\n💸 A refund has been processed for this order."

    items = order.get_items()
    if items:
        response += "\n\n**Items:**\n"
        for item in items[:5]:
            name = item.get("name", "Item")
            qty = item.get("qty", 1)
            response += f"  • {name} (x{qty})\n"

    return response


def _format_not_found_response(order_id: Optional[str], email: Optional[str]) -> str:
    """Format response when order is not found."""
    if order_id:
        return (
            f"I couldn't find order #{order_id} in our records. "
            "Could you double-check the order number? "
            "You can also try providing your email address to look up your orders."
        )
    elif email:
        return (
            f"I couldn't find any orders associated with {email}. "
            "Please verify your email address, or try providing your order number."
        )
    return (
        "I'd be happy to help you track your order! "
        "Could you please provide your order number (e.g., #ORD-12345) "
        "or the email address you used when placing the order?"
    )
