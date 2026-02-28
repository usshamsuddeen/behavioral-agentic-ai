"""
Customer Order Model — Order Data Storage
V4 NEW — Zone 8 (FR-8.1)
Stores order data for SQL lookup by the AI widget.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from app.database import Base


class CustomerOrder(Base):
    """Customer order data for e-commerce tenants."""
    __tablename__ = "customer_orders"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant Isolation (FR-7.3)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
                       nullable=False, index=True)

    # Order Identification
    order_id = Column(String(100), nullable=False, index=True)
    # Display order ID (e.g., "#ORD-12345", "SO-9876")

    # Customer Info
    customer_name = Column(String(200), nullable=True)
    customer_email = Column(String(255), nullable=True, index=True)

    # Order Status
    status = Column(String(50), default="pending")
    # pending | confirmed | shipped | delivered | cancelled | refunded

    # Financial
    total_amount = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")

    # Items (JSON array)
    items = Column(Text, default="[]")
    # [{"name": "Widget Pro", "qty": 1, "price": 29.99}]

    # Shipping
    tracking_number = Column(String(200), nullable=True)
    carrier = Column(String(100), nullable=True)
    # FedEx, UPS, DHL, TCS, etc.
    shipping_address = Column(Text, nullable=True)

    # Dates
    order_date = Column(DateTime, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    source = Column(String(50), default="csv")  # csv | api | simulator

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite index for fast lookups
    __table_args__ = (
        Index('ix_orders_tenant_orderid', 'tenant_id', 'order_id'),
        Index('ix_orders_tenant_email', 'tenant_id', 'customer_email'),
    )

    def get_items(self) -> list:
        try:
            return json.loads(self.items) if self.items else []
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "order_id": self.order_id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "status": self.status,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "items": self.get_items(),
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "shipping_address": self.shipping_address,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "notes": self.notes,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_natural_language(self) -> str:
        """Format order as natural language for AI response."""
        parts = [f"Order #{self.order_id}"]
        parts.append(f"Status: {self.status}")

        if self.order_date:
            parts.append(f"Placed on: {self.order_date.strftime('%B %d, %Y')}")
        if self.total_amount:
            parts.append(f"Total: {self.currency} {self.total_amount:.2f}")
        if self.tracking_number:
            parts.append(f"Tracking: {self.tracking_number}")
        if self.carrier:
            parts.append(f"Carrier: {self.carrier}")
        if self.estimated_delivery:
            parts.append(f"Estimated delivery: {self.estimated_delivery.strftime('%B %d, %Y')}")
        if self.shipping_address:
            parts.append(f"Shipping to: {self.shipping_address}")

        items = self.get_items()
        if items:
            item_lines = [f"  - {i.get('name', 'Item')} x{i.get('qty', 1)}" for i in items[:5]]
            parts.append("Items:\n" + "\n".join(item_lines))

        return "\n".join(parts)

    def __repr__(self):
        return f"<CustomerOrder {self.order_id} ({self.status})>"
