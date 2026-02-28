"""
Products API — Zone 3: Product Catalog Management
V4 NEW — FR-3.7

Endpoints:
  POST   /api/products                — Create single product
  POST   /api/products/upload-csv     — Bulk import via CSV
  GET    /api/products                — List products (paginated)
  GET    /api/products/{id}           — Get single product
  PUT    /api/products/{id}           — Update product
  DELETE /api/products/{id}           — Delete product
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import csv
import io
import json
import logging

from app.database import get_db
from app.models.user import User
from app.models.product_listing import ProductListing
from app.middleware.jwt import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["Products"])


class CreateProductRequest(BaseModel):
    name: str = Field(..., max_length=500)
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = Field("USD", max_length=10)
    category: Optional[str] = None
    sku: Optional[str] = None
    in_stock: bool = True
    stock_quantity: int = 0
    images: List[str] = []
    attributes: dict = {}


def _auto_index_product(product: ProductListing, tenant_id: int):
    """Auto-index product to vector store for RAG retrieval (non-blocking)."""
    try:
        from app.knowledge.manager import get_knowledge_manager
        manager = get_knowledge_manager()
        product_text = (
            f"Product: {product.name}\n"
            f"Description: {product.description or 'N/A'}\n"
            f"Price: {product.currency} {product.price}\n"
            f"Category: {product.category or 'N/A'}\n"
            f"SKU: {product.sku or 'N/A'}\n"
            f"In Stock: {'Yes' if product.in_stock else 'No'}\n"
            f"Attributes: {product.attributes or '{}'}"
        )
        manager.upload_document(
            client_id=str(tenant_id),
            content=product_text.encode("utf-8"),
            filename=f"product_{product.sku or product.id}.txt",
            doc_type="product",
            category="product"
        )
        logger.info(f"Auto-indexed product {product.name} to vector store")
    except Exception as e:
        logger.warning(f"Product auto-index failed (non-blocking): {e}")


@router.post("")
async def create_product(
    request: CreateProductRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a single product listing."""
    product = ProductListing(
        tenant_id=current_user.tenant_id,
        name=request.name,
        description=request.description,
        price=request.price,
        currency=request.currency,
        category=request.category,
        sku=request.sku,
        in_stock=request.in_stock,
        stock_quantity=request.stock_quantity,
        images=json.dumps(request.images),
        attributes=json.dumps(request.attributes),
        source="manual"
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # ★ V4: Auto-index to vector store for RAG retrieval
    _auto_index_product(product, current_user.tenant_id)

    return {"success": True, "product": product.to_dict()}


@router.post("/upload-csv")
async def upload_product_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk import products from CSV."""
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            product = ProductListing(
                tenant_id=current_user.tenant_id,
                name=row.get("name", row.get("Name", row.get("product_name", ""))),
                description=row.get("description", row.get("Description", "")),
                price=float(row.get("price", row.get("Price", 0)) or 0),
                currency=row.get("currency", "USD"),
                category=row.get("category", row.get("Category", "")),
                sku=row.get("sku", row.get("SKU", "")),
                in_stock=row.get("in_stock", "true").lower() in ("true", "yes", "1"),
                stock_quantity=int(row.get("stock_quantity", row.get("quantity", 0)) or 0),
                source="csv"
            )
            db.add(product)
            created += 1
        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    db.commit()

    # ★ V4: Auto-index all imported products to vector store
    products = db.query(ProductListing).filter(
        ProductListing.tenant_id == current_user.tenant_id,
        ProductListing.source == "csv"
    ).order_by(ProductListing.created_at.desc()).limit(created).all()
    for product in products:
        _auto_index_product(product, current_user.tenant_id)

    return {
        "success": True,
        "created": created,
        "errors": errors[:10],
        "total_rows": created + len(errors)
    }


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List products for the current tenant."""
    query = db.query(ProductListing).filter(ProductListing.tenant_id == current_user.tenant_id)

    if search:
        query = query.filter(
            ProductListing.name.ilike(f"%{search}%") |
            ProductListing.sku.ilike(f"%{search}%")
        )
    if category:
        query = query.filter(ProductListing.category == category)

    total = query.count()
    products = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "products": [p.to_dict() for p in products],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single product by ID."""
    product = db.query(ProductListing).filter(
        ProductListing.id == product_id,
        ProductListing.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return {"product": product.to_dict()}


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    request: CreateProductRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a product."""
    product = db.query(ProductListing).filter(
        ProductListing.id == product_id,
        ProductListing.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")

    product.name = request.name
    product.description = request.description
    product.price = request.price
    product.currency = request.currency
    product.category = request.category
    product.sku = request.sku
    product.in_stock = request.in_stock
    product.stock_quantity = request.stock_quantity
    product.images = json.dumps(request.images)
    product.attributes = json.dumps(request.attributes)
    db.commit()
    db.refresh(product)

    # ★ V4: Auto-re-index to vector store
    _auto_index_product(product, current_user.tenant_id)

    return {"success": True, "product": product.to_dict()}


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a product."""
    product = db.query(ProductListing).filter(
        ProductListing.id == product_id,
        ProductListing.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    db.commit()
    return {"success": True, "deleted": product_id}
