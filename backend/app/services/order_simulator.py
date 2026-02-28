"""
Order Simulator — Generate Realistic Demo Orders
V4 NEW — Zone 8 (FR-8.2)

Creates realistic fake order data for FYP demo and testing.
"""

import random
import string
from datetime import datetime, timedelta
from typing import List, Dict
import json
import logging

from app.models.order import CustomerOrder

logger = logging.getLogger(__name__)

# Realistic data pools
FIRST_NAMES = [
    "Ahmed", "Fatima", "John", "Sarah", "Ali", "Maria", "Hassan", "Ayesha",
    "David", "Emily", "Muhammad", "Zainab", "James", "Sophia", "Usman",
    "Hira", "Michael", "Emma", "Omar", "Aisha", "Robert", "Olivia",
    "Ibrahim", "Maryam", "William", "Ava", "Hamza", "Khadija",
]

LAST_NAMES = [
    "Khan", "Ahmed", "Smith", "Johnson", "Ali", "Malik", "Williams",
    "Brown", "Davis", "Shah", "Hussain", "Wilson", "Anderson", "Qureshi",
    "Iqbal", "Siddiqui", "Taylor", "Thomas", "Garcia", "Martinez",
]

PRODUCT_CATALOG = [
    {"name": "Wireless Earbuds Pro", "price": 49.99, "category": "Electronics"},
    {"name": "Smart Watch Ultra", "price": 199.99, "category": "Electronics"},
    {"name": "Cotton T-Shirt", "price": 24.99, "category": "Clothing"},
    {"name": "Running Shoes", "price": 89.99, "category": "Footwear"},
    {"name": "Laptop Stand", "price": 39.99, "category": "Accessories"},
    {"name": "Phone Case", "price": 14.99, "category": "Accessories"},
    {"name": "Yoga Mat", "price": 29.99, "category": "Fitness"},
    {"name": "Water Bottle", "price": 19.99, "category": "Kitchen"},
    {"name": "Bluetooth Speaker", "price": 59.99, "category": "Electronics"},
    {"name": "Backpack", "price": 54.99, "category": "Bags"},
    {"name": "LED Desk Lamp", "price": 34.99, "category": "Home"},
    {"name": "Protein Powder", "price": 44.99, "category": "Health"},
    {"name": "Sunglasses", "price": 29.99, "category": "Accessories"},
    {"name": "Hoodie", "price": 49.99, "category": "Clothing"},
    {"name": "USB-C Cable", "price": 9.99, "category": "Electronics"},
]

CARRIERS = ["FedEx", "UPS", "DHL", "USPS", "TCS", "Royal Mail", "Australia Post"]

STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled", "refunded"]
STATUS_WEIGHTS = [15, 20, 25, 30, 5, 5]  # Realistic distribution

CURRENCIES = ["USD", "EUR", "GBP", "PKR", "AED"]
CURRENCY_WEIGHTS = [40, 20, 15, 15, 10]


def generate_orders(tenant_id: int, count: int = 50) -> List[CustomerOrder]:
    """
    Generate realistic demo orders for a tenant.

    Args:
        tenant_id: Tenant to generate orders for
        count: Number of orders to generate (10-200)

    Returns:
        List of CustomerOrder objects (not yet committed)
    """
    count = max(10, min(count, 200))
    orders = []

    for i in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email_domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"])
        email = f"{first.lower()}.{last.lower()}@{email_domain}"

        # Generate order ID
        prefix = random.choice(["ORD", "SO", "INV", ""])
        number = random.randint(10000, 99999)
        order_id = f"{prefix}-{number}" if prefix else str(number)

        # Status with realistic distribution
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

        # Items (1-4 random products)
        num_items = random.randint(1, 4)
        items = []
        total = 0.0
        for _ in range(num_items):
            product = random.choice(PRODUCT_CATALOG)
            qty = random.randint(1, 3)
            items.append({"name": product["name"], "qty": qty, "price": product["price"]})
            total += product["price"] * qty

        # Currency
        currency = random.choices(CURRENCIES, weights=CURRENCY_WEIGHTS, k=1)[0]

        # Dates
        order_date = datetime.utcnow() - timedelta(days=random.randint(1, 60))
        estimated_delivery = order_date + timedelta(days=random.randint(3, 14))

        # Tracking (only if shipped or delivered)
        tracking = None
        carrier = None
        if status in ("shipped", "delivered"):
            tracking = ''.join(random.choices(string.digits, k=12))
            carrier = random.choice(CARRIERS)

        order = CustomerOrder(
            tenant_id=tenant_id,
            order_id=order_id,
            customer_name=f"{first} {last}",
            customer_email=email,
            status=status,
            total_amount=round(total, 2),
            currency=currency,
            items=json.dumps(items),
            tracking_number=tracking,
            carrier=carrier,
            shipping_address=f"{random.randint(1, 999)} Main Street, City, Country",
            order_date=order_date,
            estimated_delivery=estimated_delivery,
            notes=None,
            source="simulator"
        )
        orders.append(order)

    logger.info(f"Generated {len(orders)} demo orders for tenant {tenant_id}")
    return orders
