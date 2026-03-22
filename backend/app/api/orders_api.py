"""
Orders API — Zone 8: Universal Order Data Gateway
V4 NEW — FR-8.1, FR-8.2, FR-8.3

Endpoints:
  POST   /api/orders/upload-csv    — Upload order CSV (fuzzy column matching)
  GET    /api/orders               — List orders (paginated, searchable)
  GET    /api/orders/{order_id}    — Get single order details
  DELETE /api/orders/{order_id}    — Delete an order
  POST   /api/orders/push          — External system pushes order (API Key auth)
  POST   /api/orders/push/batch    — External system pushes batch orders (API Key auth)
  POST   /api/orders/simulate      — Generate demo orders (simulator)
  GET    /api/orders/stats         — Order statistics
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, Header, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from difflib import SequenceMatcher
import csv
import io
import json
import logging
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.order import CustomerOrder
from app.middleware.jwt import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["Orders"])

MAX_CSV_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 10000

# ═══════════════════════════════════════════════════════════════
# FUZZY COLUMN MATCHING — Maps any CSV header to our schema
# ═══════════════════════════════════════════════════════════════

COLUMN_ALIASES = {
    "order_id": [
        "order id", "order number", "order #", "order_number", "ordernumber",
        "id", "reference", "order ref", "invoice", "invoice number",
        "order no", "po number", "purchase order", "confirmation number",
        "transaction id", "transaction number", "receipt number",
        "order code", "ref no", "reference number", "order reference",
        "booking id", "booking number", "po", "po#",
    ],
    "customer_name": [
        "name", "customer name", "customer", "buyer", "ship to name",
        "billing name", "full name", "recipient", "client name", "client",
        "purchaser", "consumer", "contact name", "ordered by", "shopper",
        "account name", "bill to name", "ship to", "bill to", "deliver to",
        "first name", "last name", "customer full name", "contact",
    ],
    "customer_email": [
        "email", "e-mail", "customer email", "buyer email",
        "contact email", "email address", "mail", "customer e-mail",
        "buyer e-mail", "user email", "account email",
        "notification email", "billing email", "shipping email",
        "contact e-mail", "email id",
    ],
    "status": [
        "status", "order status", "fulfillment", "fulfillment status",
        "delivery status", "state", "payment status", "shipment status",
        "processing status", "current status", "stage", "progress",
        "condition", "order state", "workflow status", "order stage",
    ],
    "total_amount": [
        "total", "amount", "order total", "grand total", "price",
        "subtotal", "order value", "total price", "net total",
        "gross total", "total cost", "final amount", "payment amount",
        "invoice total", "bill amount", "order amount", "charged amount",
        "paid amount", "total due", "sum", "total sum", "net amount",
        "gross amount", "revenue",
    ],
    "currency": [
        "currency", "currency code", "currency type", "price currency",
        "money code", "curr", "iso currency", "payment currency",
    ],
    "tracking_number": [
        "tracking", "tracking number", "tracking #", "tracking_number",
        "awb", "consignment", "tracking id", "tracking code",
        "tracking no", "shipment tracking", "consignment number",
        "waybill", "airway bill", "shipping number", "parcel tracking",
        "track id", "tracking ref", "shipment number", "consignment no",
    ],
    "carrier": [
        "carrier", "shipping carrier", "courier", "shipping method",
        "delivery service", "logistics", "shipping provider",
        "delivery company", "delivery partner", "freight", "shipper",
        "transport", "postal service", "express service",
        "shipping service", "logistics provider", "delivery method",
        "ship via", "ship method",
    ],
    "shipping_address": [
        "address", "shipping address", "delivery address",
        "ship to address", "ship address", "mailing address",
        "postal address", "street address", "destination",
        "delivery location", "customer address", "billing address",
        "full address", "street", "address line",
        "deliver to address", "shipment address",
    ],
    "order_date": [
        "date", "order date", "created", "created at", "placed on",
        "purchase date", "order created", "transaction date",
        "sale date", "invoice date", "placed date", "ordered on",
        "created date", "date ordered", "date placed",
        "submission date", "booking date", "ordered at",
        "timestamp", "order timestamp", "payment date",
    ],
    "items": [
        "items", "products", "line items", "order items",
        "ordered items", "purchased items", "product list",
        "item list", "cart items", "basket items", "order details",
        "order lines", "sku list", "item details",
        "purchased products", "bought items", "goods",
    ],
    "notes": [
        "notes", "comments", "internal notes", "remarks", "memo",
        "order notes", "customer notes", "special instructions",
        "instructions", "message", "additional info",
        "order comments", "delivery notes", "shipping notes",
        "gift message", "order memo", "annotation",
    ],
}


def fuzzy_match_column(header: str) -> Optional[str]:
    """Match a CSV header to our schema column using fuzzy matching."""
    # Normalize: lowercase, strip, replace _/- with spaces, collapse whitespace
    header_lower = " ".join(header.lower().strip().replace("_", " ").replace("-", " ").split())

    # 1. Exact match first
    for column, aliases in COLUMN_ALIASES.items():
        if header_lower in aliases or header_lower == column:
            return column

    # 2. Substring containment match
    for column, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in header_lower or header_lower in alias:
                return column

    # 3. SequenceMatcher fuzzy scoring (threshold 0.7)
    best_match = None
    best_score = 0.0

    for column, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            score = SequenceMatcher(None, header_lower, alias).ratio()
            if score > best_score and score > 0.7:
                best_score = score
                best_match = column

    return best_match


# ═══════════════════════════════════════════════════════════════
# AUTO-INDEX ORDER TO RAG VECTOR STORE
# ═══════════════════════════════════════════════════════════════

def _auto_index_order(order: CustomerOrder, tenant_id: int):
    """Auto-index order to vector store for RAG retrieval (non-blocking)."""
    try:
        from app.knowledge.manager import get_knowledge_manager
        manager = get_knowledge_manager()
        order_text = (
            f"Order ID: {order.order_id}\n"
            f"Customer Name: {order.customer_name or 'N/A'}\n"
            f"Customer Email: {order.customer_email or 'N/A'}\n"
            f"Status: {order.status or 'pending'}\n"
            f"Total Amount: {order.currency or 'USD'} {order.total_amount or 0}\n"
            f"Tracking Number: {order.tracking_number or 'N/A'}\n"
            f"Carrier: {order.carrier or 'N/A'}\n"
            f"Shipping Address: {order.shipping_address or 'N/A'}\n"
            f"Order Date: {order.order_date or 'N/A'}\n"
            f"Notes: {order.notes or 'N/A'}"
        )
        manager.upload_document(
            client_id=str(tenant_id),
            content=order_text.encode("utf-8"),
            filename=f"order_{order.order_id}.txt",
            doc_type="order",
            category="order"
        )
        logger.info(f"Auto-indexed order {order.order_id} to vector store")
    except Exception as e:
        logger.warning(f"Order auto-index failed (non-blocking): {e}")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/upload-csv")
async def upload_order_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload orders via CSV with fuzzy column matching."""
    content = await file.read()

    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(400, f"CSV too large (max {MAX_CSV_SIZE // 1024 // 1024}MB)")

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    # Map CSV headers to our schema
    column_map = {}
    if reader.fieldnames:
        for header in reader.fieldnames:
            mapped = fuzzy_match_column(header)
            if mapped:
                column_map[header] = mapped

    created = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            break
        try:
            mapped_row = {}
            for csv_col, our_col in column_map.items():
                mapped_row[our_col] = row.get(csv_col, "").strip()

            if not mapped_row.get("order_id"):
                skipped += 1
                continue

            order_date = None
            if mapped_row.get("order_date"):
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        order_date = datetime.strptime(mapped_row["order_date"], fmt)
                        break
                    except ValueError:
                        continue

            order = CustomerOrder(
                tenant_id=current_user.tenant_id,
                order_id=mapped_row.get("order_id", ""),
                customer_name=mapped_row.get("customer_name", ""),
                customer_email=mapped_row.get("customer_email", ""),
                status=mapped_row.get("status", "pending").lower(),
                total_amount=float(mapped_row.get("total_amount", 0) or 0),
                currency=mapped_row.get("currency", "USD"),
                tracking_number=mapped_row.get("tracking_number"),
                carrier=mapped_row.get("carrier"),
                shipping_address=mapped_row.get("shipping_address"),
                order_date=order_date,
                notes=mapped_row.get("notes"),
                source="csv"
            )
            db.add(order)
            created += 1
        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    db.commit()

    # ★ V4: Auto-index all imported orders to vector store for RAG
    orders_to_index = db.query(CustomerOrder).filter(
        CustomerOrder.tenant_id == current_user.tenant_id,
        CustomerOrder.source == "csv"
    ).order_by(CustomerOrder.created_at.desc()).limit(created).all()
    for order in orders_to_index:
        _auto_index_order(order, current_user.tenant_id)

    return {
        "success": True,
        "created": created,
        "skipped": skipped,
        "errors": errors[:10],
        "column_mapping": column_map,
    }


@router.get("")
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = Query(None, description="Filter by source: csv, api, widget, sync, simulator"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List orders for the current tenant."""
    query = db.query(CustomerOrder).filter(
        CustomerOrder.tenant_id == current_user.tenant_id
    )

    if search:
        query = query.filter(
            CustomerOrder.order_id.ilike(f"%{search}%") |
            CustomerOrder.customer_email.ilike(f"%{search}%") |
            CustomerOrder.customer_name.ilike(f"%{search}%")
        )
    if status:
        query = query.filter(CustomerOrder.status == status)
    if source:
        query = query.filter(CustomerOrder.source == source)

    total = query.count()
    orders = query.order_by(
        CustomerOrder.created_at.desc()
    ).offset((page - 1) * limit).limit(limit).all()

    return {
        "orders": [o.to_dict() for o in orders],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/stats")
async def order_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order statistics."""
    base = db.query(CustomerOrder).filter(
        CustomerOrder.tenant_id == current_user.tenant_id
    )

    total = base.count()
    by_status = db.query(
        CustomerOrder.status, func.count(CustomerOrder.id)
    ).filter(
        CustomerOrder.tenant_id == current_user.tenant_id
    ).group_by(CustomerOrder.status).all()

    return {
        "total": total,
        "by_status": {s: c for s, c in by_status},
    }


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single order by ID."""
    order = db.query(CustomerOrder).filter(
        CustomerOrder.tenant_id == current_user.tenant_id,
        CustomerOrder.order_id == order_id
    ).first()

    if not order:
        raise HTTPException(404, "Order not found")
    return {"order": order.to_dict()}


@router.delete("/{order_db_id}")
async def delete_order(
    order_db_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an order by database ID."""
    order = db.query(CustomerOrder).filter(
        CustomerOrder.id == order_db_id,
        CustomerOrder.tenant_id == current_user.tenant_id
    ).first()

    if not order:
        raise HTTPException(404, "Order not found")

    db.delete(order)
    db.commit()
    return {"success": True, "deleted_order_id": order.order_id}


class SimulateRequest(BaseModel):
    count: int = Field(50, ge=10, le=200)


@router.post("/simulate")
async def simulate_orders(
    request: SimulateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate demo orders using the simulator."""
    from app.services.order_simulator import generate_orders

    orders = generate_orders(
        tenant_id=current_user.tenant_id,
        count=request.count
    )

    for order in orders:
        db.add(order)
    db.commit()

    # ★ V4: Auto-index simulated orders to vector store for RAG
    for order in orders:
        _auto_index_order(order, current_user.tenant_id)

    return {
        "success": True,
        "count": len(orders),
        "message": f"Generated {len(orders)} demo orders"
    }


class PushOrderRequest(BaseModel):
    order_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: str = "pending"
    total_amount: Optional[float] = None
    currency: str = "USD"
    items: list = []
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None


@router.post("/push")
async def push_order(
    request: PushOrderRequest,
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
    db: Session = Depends(get_db)
):
    """External system pushes a single order. Auth: Widget API Key."""
    from app.api.widget_api import get_tenant_by_api_key

    tenant = get_tenant_by_api_key(x_widget_key, db)

    order = CustomerOrder(
        tenant_id=tenant.id,
        order_id=request.order_id,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        status=request.status,
        total_amount=request.total_amount,
        currency=request.currency,
        items=json.dumps(request.items),
        tracking_number=request.tracking_number,
        carrier=request.carrier,
        source="api"
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # ★ V5 FIX: Auto-index to vector store for RAG retrieval
    _auto_index_order(order, tenant.id)

    return {"success": True, "order": order.to_dict()}


@router.post("/push/batch")
async def push_orders_batch(
    orders: List[PushOrderRequest] = Body(...),
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
    db: Session = Depends(get_db)
):
    """External system pushes multiple orders in one request. Auth: Widget API Key."""
    from app.api.widget_api import get_tenant_by_api_key

    tenant = get_tenant_by_api_key(x_widget_key, db)
    created = 0
    errors = []

    for i, req in enumerate(orders[:500]):  # Max 500 per batch
        try:
            order = CustomerOrder(
                tenant_id=tenant.id,
                order_id=req.order_id,
                customer_name=req.customer_name,
                customer_email=req.customer_email,
                status=req.status,
                total_amount=req.total_amount,
                currency=req.currency,
                items=json.dumps(req.items),
                tracking_number=req.tracking_number,
                carrier=req.carrier,
                source="api"
            )
            db.add(order)
            created += 1
        except Exception as e:
            errors.append(f"Order {i+1}: {str(e)}")

    db.commit()

    # ★ V5 FIX: Auto-index all batch-pushed orders to vector store
    batch_orders = db.query(CustomerOrder).filter(
        CustomerOrder.tenant_id == tenant.id,
        CustomerOrder.source == "api"
    ).order_by(CustomerOrder.created_at.desc()).limit(created).all()
    for order in batch_orders:
        _auto_index_order(order, tenant.id)

    return {
        "success": True,
        "created": created,
        "errors": errors[:10],
        "total_submitted": len(orders)
    }
