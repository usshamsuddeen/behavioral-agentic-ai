"""
Product Listing Model — Structured Product Catalog
V4 NEW — Zone 3 (FR-3.7)
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from app.database import Base


class ProductListing(Base):
    """Product catalog for e-commerce tenants."""
    __tablename__ = "product_listings"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant Isolation
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Product Info
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    category = Column(String(200), nullable=True)
    sku = Column(String(100), nullable=True, index=True)

    # Stock
    in_stock = Column(Boolean, default=True)
    stock_quantity = Column(Integer, default=0)

    # Media & Attributes (JSON)
    images = Column(Text, default="[]")        # JSON array of image URLs
    attributes = Column(Text, default="{}")    # JSON dict of attributes

    # Source
    source = Column(String(50), default="manual")  # manual / csv / api

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_images(self) -> list:
        try:
            return json.loads(self.images) if self.images else []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_attributes(self) -> dict:
        try:
            return json.loads(self.attributes) if self.attributes else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
            "category": self.category,
            "sku": self.sku,
            "in_stock": self.in_stock,
            "stock_quantity": self.stock_quantity,
            "images": self.get_images(),
            "attributes": self.get_attributes(),
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ProductListing {self.name} ({self.sku})>"
