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
from difflib import SequenceMatcher

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
    image_url: Optional[str] = None  # Single image URL (frontend sends this)
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
        # Append image URL tag so the LLM can pass it through in responses
        images = product.get_images()
        if images and images[0]:
            product_text += f"\n[IMAGE:{images[0]}]"
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
    # Merge image_url into images list
    all_images = list(request.images)
    if request.image_url and request.image_url not in all_images:
        all_images.insert(0, request.image_url)

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
        images=json.dumps(all_images),
        attributes=json.dumps(request.attributes),
        source="manual"
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # ★ V4: Auto-index to vector store for RAG retrieval
    _auto_index_product(product, current_user.tenant_id)

    return {"success": True, "product": product.to_dict()}


# ═══════════════════════════════════════════════════════════════
# FUZZY COLUMN MATCHING — Maps any CSV header to our schema
# Supports: exact match → substring containment → SequenceMatcher
# ═══════════════════════════════════════════════════════════════

PRODUCT_COLUMN_ALIASES = {
    "name": [
        "name", "product name", "title", "product title", "product_name",
        "item name", "item", "product", "product label", "listing name",
        "listing title", "item title", "goods name", "merchandise",
        "display name", "headline", "handle",
    ],
    "description": [
        "description", "desc", "product description", "details",
        "body html", "body", "summary", "product details",
        "long description", "short description", "overview", "about",
        "info", "product info", "item description", "features",
        "specification", "specs", "product summary", "content",
        "body text", "detail",
    ],
    "price": [
        "price", "unit price", "cost", "amount", "sale price",
        "regular price", "variant price", "retail price", "msrp",
        "selling price", "list price", "item price", "product price",
        "base price", "net price", "gross price", "mrp", "rate",
        "unit cost", "buy price", "wholesale price", "discount price",
        "offer price", "special price",
    ],
    "currency": [
        "currency", "currency code", "currency type", "price currency",
        "money code", "curr", "iso currency",
    ],
    "category": [
        "category", "product category", "type", "product type",
        "collection", "department", "group", "subcategory", "sub category",
        "product group", "product class", "classification", "class",
        "genre", "segment", "product line", "family", "catalog",
        "section", "division",
    ],
    "sku": [
        "sku", "product sku", "variant sku", "item number",
        "article number", "part number", "barcode", "upc", "ean",
        "model number", "product id", "product code", "item code",
        "reference", "ref", "product ref", "catalog number",
        "stock code", "material number", "asin", "isbn", "gtin",
        "mpn", "manufacturer part",
    ],
    "in_stock": [
        "in stock", "in_stock", "available", "availability",
        "stock status", "is available", "stocked", "in inventory",
        "on hand", "available stock", "is in stock", "stock available",
        "can purchase", "purchasable", "sellable", "active",
    ],
    "stock_quantity": [
        "stock quantity", "stock_quantity", "quantity", "qty",
        "inventory", "stock", "units", "inventory qty",
        "quantity on hand", "qty on hand", "available qty",
        "stock count", "stock level", "inventory count", "unit count",
        "available units", "warehouse qty", "on hand qty",
        "remaining stock", "remaining qty", "quantity available",
    ],
    "image_url": [
        "image", "image url", "image_url", "images", "image src",
        "photo", "picture", "thumbnail", "product image", "variant image",
        "img", "img url", "main image", "primary image", "featured image",
        "image link", "photo url", "pic", "cover image", "gallery",
        "media", "media url", "image path", "img src", "product photo",
        "product pic",
    ],
}


def _fuzzy_match_product_column(header: str):
    """Match a CSV header to our product schema column using fuzzy matching."""
    # Normalize: lowercase, strip, replace _/- with spaces, collapse whitespace
    header_lower = " ".join(header.strip().lower().replace("_", " ").replace("-", " ").split())

    # 1. Exact match against field names and aliases
    for field, aliases in PRODUCT_COLUMN_ALIASES.items():
        if header_lower == field:
            return field
        for alias in aliases:
            if header_lower == alias:
                return field

    # 2. Substring containment match
    for field, aliases in PRODUCT_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in header_lower or header_lower in alias:
                return field

    # 3. SequenceMatcher fuzzy scoring (threshold 0.7)
    best_match = None
    best_score = 0.0
    for field, aliases in PRODUCT_COLUMN_ALIASES.items():
        for alias in aliases:
            score = SequenceMatcher(None, header_lower, alias).ratio()
            if score > best_score and score > 0.7:
                best_score = score
                best_match = field

    return best_match


@router.post("/upload-csv")
async def upload_product_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk import products from CSV with fuzzy column matching."""
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    # Map CSV headers to our schema
    column_map = {}
    if reader.fieldnames:
        for header in reader.fieldnames:
            mapped = _fuzzy_match_product_column(header)
            if mapped:
                column_map[header] = mapped

    created = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            mapped_row = {}
            for csv_col, our_col in column_map.items():
                mapped_row[our_col] = row.get(csv_col, "").strip()

            name = mapped_row.get("name", "")
            if not name:
                errors.append(f"Row {i+1}: Missing product name")
                continue

            in_stock_val = mapped_row.get("in_stock", "true").lower()
            image_url = mapped_row.get("image_url", "")

            product = ProductListing(
                tenant_id=current_user.tenant_id,
                name=name,
                description=mapped_row.get("description", ""),
                price=float(mapped_row.get("price", 0) or 0),
                currency=mapped_row.get("currency", "USD") or "USD",
                category=mapped_row.get("category", ""),
                sku=mapped_row.get("sku", ""),
                in_stock=in_stock_val in ("true", "yes", "1", "in stock", "available"),
                stock_quantity=int(mapped_row.get("stock_quantity", 0) or 0),
                images=json.dumps([image_url] if image_url else []),
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
        "total_rows": created + len(errors),
        "column_mapping": column_map,
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

    # Merge image_url into images list
    all_images = list(request.images)
    if request.image_url and request.image_url not in all_images:
        all_images.insert(0, request.image_url)

    product.name = request.name
    product.description = request.description
    product.price = request.price
    product.currency = request.currency
    product.category = request.category
    product.sku = request.sku
    product.in_stock = request.in_stock
    product.stock_quantity = request.stock_quantity
    product.images = json.dumps(all_images)
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
