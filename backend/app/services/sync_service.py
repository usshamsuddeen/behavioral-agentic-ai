"""
Sync Service — V5 NEW
Handles real-time CSV sync from external stores for Orders and Products.
Supports upsert logic, fuzzy column matching, and auto-indexing to vector store.

Author: Behavioral Agentic AI Team
Version: 5.0.0
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
import re
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.models.sync_config import SyncConfig
from app.models.order import CustomerOrder
from app.models.product_listing import ProductListing

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _safe_float(val, default=0.0) -> float:
    """Parse a float value, stripping currency symbols and commas."""
    if not val:
        return default
    try:
        cleaned = re.sub(r'[^\d.\-]', '', str(val))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════
# CORE SYNC ENGINE
# ═══════════════════════════════════════════════════════════════

async def sync_orders(config: SyncConfig, db: Session) -> dict:
    """
    Fetch CSV from external URL and upsert orders.

    Returns:
        dict with created, updated, errors, skipped counts
    """
    config.last_sync_status = "running"
    db.commit()

    try:
        # Fetch CSV
        csv_text = await _fetch_csv(config)
        reader = csv.DictReader(io.StringIO(csv_text))

        # Build column mapping (reuse orders_api logic)
        from app.api.orders_api import fuzzy_match_column
        column_map = {}
        if reader.fieldnames:
            for header in reader.fieldnames:
                mapped = fuzzy_match_column(header)
                if mapped:
                    column_map[header] = mapped

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader):
            if i >= 10000:  # Safety limit
                break
            try:
                mapped_row = {}
                for csv_col, our_col in column_map.items():
                    mapped_row[our_col] = row.get(csv_col, "").strip()

                order_id = mapped_row.get("order_id")
                if not order_id:
                    skipped += 1
                    continue

                # Parse date
                order_date = None
                if mapped_row.get("order_date"):
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
                        try:
                            order_date = datetime.strptime(mapped_row["order_date"], fmt)
                            break
                        except ValueError:
                            continue

                # UPSERT: check if order exists
                existing = db.query(CustomerOrder).filter(
                    CustomerOrder.tenant_id == config.tenant_id,
                    CustomerOrder.order_id == order_id,
                ).first()

                if existing:
                    # UPDATE existing order
                    if mapped_row.get("status"):
                        existing.status = mapped_row["status"].lower()
                    if mapped_row.get("tracking_number"):
                        existing.tracking_number = mapped_row["tracking_number"]
                    if mapped_row.get("carrier"):
                        existing.carrier = mapped_row["carrier"]
                    if mapped_row.get("total_amount"):
                        try:
                            existing.total_amount = float(mapped_row["total_amount"])
                        except (ValueError, TypeError):
                            pass
                    if mapped_row.get("shipping_address"):
                        existing.shipping_address = mapped_row["shipping_address"]
                    if mapped_row.get("notes"):
                        existing.notes = mapped_row["notes"]
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # CREATE new order
                    order = CustomerOrder(
                        tenant_id=config.tenant_id,
                        order_id=order_id,
                        customer_name=mapped_row.get("customer_name", ""),
                        customer_email=mapped_row.get("customer_email", ""),
                        status=mapped_row.get("status", "pending").lower(),
                        total_amount=_safe_float(mapped_row.get("total_amount", 0)),
                        currency=mapped_row.get("currency", "USD"),
                        tracking_number=mapped_row.get("tracking_number"),
                        carrier=mapped_row.get("carrier"),
                        shipping_address=mapped_row.get("shipping_address"),
                        order_date=order_date,
                        notes=mapped_row.get("notes"),
                        source="sync",
                    )
                    db.add(order)
                    created += 1

            except Exception as e:
                errors.append(f"Row {i+1}: {str(e)}")

        db.commit()

        # Auto-index new and updated orders to vector store
        try:
            from app.api.orders_api import _auto_index_order
            recent_orders = db.query(CustomerOrder).filter(
                CustomerOrder.tenant_id == config.tenant_id,
                CustomerOrder.source == "sync",
            ).order_by(CustomerOrder.updated_at.desc()).limit(created + updated).all()
            for order in recent_orders:
                _auto_index_order(order, config.tenant_id)
        except Exception as idx_err:
            logger.warning(f"Sync order indexing failed (non-blocking): {idx_err}")

        # Update config status
        config.last_synced_at = datetime.utcnow()
        config.last_sync_status = "success"
        config.last_sync_created = created
        config.last_sync_updated = updated
        config.last_sync_message = f"Synced: {created} created, {updated} updated, {skipped} skipped"
        if errors:
            config.last_sync_message += f" ({len(errors)} errors)"
        db.commit()

        logger.info(f"✅ Order sync complete: tenant={config.tenant_id} created={created} updated={updated}")
        return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:10]}

    except Exception as e:
        config.last_sync_status = "failed"
        config.last_sync_message = str(e)[:500]
        config.last_synced_at = datetime.utcnow()
        db.commit()
        logger.error(f"❌ Order sync failed: {e}")
        return {"created": 0, "updated": 0, "errors": [str(e)]}


async def sync_products(config: SyncConfig, db: Session) -> dict:
    """
    Fetch CSV from external URL and upsert products.
    """
    config.last_sync_status = "running"
    db.commit()

    try:
        csv_text = await _fetch_csv(config)
        reader = csv.DictReader(io.StringIO(csv_text))

        # Build column mapping (reuse products_api logic)
        from app.api.products_api import _fuzzy_match_product_column
        column_map = {}
        if reader.fieldnames:
            for header in reader.fieldnames:
                mapped = _fuzzy_match_product_column(header)
                if mapped:
                    column_map[header] = mapped

        created = 0
        updated = 0
        errors = []

        for i, row in enumerate(reader):
            if i >= 10000:
                break
            try:
                mapped_row = {}
                for csv_col, our_col in column_map.items():
                    mapped_row[our_col] = row.get(csv_col, "").strip()

                name = mapped_row.get("name", "")
                if not name:
                    continue

                sku = mapped_row.get("sku", "")
                in_stock_val = mapped_row.get("in_stock", "true").lower()
                image_url = mapped_row.get("image_url", "")

                # UPSERT: match by SKU (if available) or name
                existing = None
                if sku:
                    existing = db.query(ProductListing).filter(
                        ProductListing.tenant_id == config.tenant_id,
                        ProductListing.sku == sku,
                    ).first()
                if not existing:
                    existing = db.query(ProductListing).filter(
                        ProductListing.tenant_id == config.tenant_id,
                        ProductListing.name == name,
                    ).first()

                if existing:
                    # UPDATE existing product
                    existing.name = name
                    if mapped_row.get("description"):
                        existing.description = mapped_row["description"]
                    if mapped_row.get("price"):
                        try:
                            existing.price = float(mapped_row["price"])
                        except (ValueError, TypeError):
                            pass
                    if mapped_row.get("currency"):
                        existing.currency = mapped_row["currency"]
                    if mapped_row.get("category"):
                        existing.category = mapped_row["category"]
                    if sku:
                        existing.sku = sku
                    existing.in_stock = in_stock_val in ("true", "yes", "1", "in stock", "available")
                    if mapped_row.get("stock_quantity"):
                        try:
                            existing.stock_quantity = int(mapped_row["stock_quantity"])
                        except (ValueError, TypeError):
                            pass
                    if image_url:
                        existing.images = json.dumps([image_url])
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # CREATE new product
                    product = ProductListing(
                        tenant_id=config.tenant_id,
                        name=name,
                        description=mapped_row.get("description", ""),
                        price=_safe_float(mapped_row.get("price", 0)),
                        currency=mapped_row.get("currency", "USD") or "USD",
                        category=mapped_row.get("category", ""),
                        sku=sku,
                        in_stock=in_stock_val in ("true", "yes", "1", "in stock", "available"),
                        stock_quantity=int(mapped_row.get("stock_quantity", 0) or 0),
                        images=json.dumps([image_url] if image_url else []),
                        source="sync",
                    )
                    db.add(product)
                    created += 1

            except Exception as e:
                errors.append(f"Row {i+1}: {str(e)}")

        db.commit()

        # Auto-index to vector store
        try:
            from app.api.products_api import _auto_index_product
            recent_products = db.query(ProductListing).filter(
                ProductListing.tenant_id == config.tenant_id,
                ProductListing.source == "sync",
            ).order_by(ProductListing.updated_at.desc()).limit(created + updated).all()
            for product in recent_products:
                _auto_index_product(product, config.tenant_id)
        except Exception as idx_err:
            logger.warning(f"Sync product indexing failed (non-blocking): {idx_err}")

        # Update config status
        config.last_synced_at = datetime.utcnow()
        config.last_sync_status = "success"
        config.last_sync_created = created
        config.last_sync_updated = updated
        config.last_sync_message = f"Synced: {created} created, {updated} updated"
        if errors:
            config.last_sync_message += f" ({len(errors)} errors)"
        db.commit()

        logger.info(f"✅ Product sync complete: tenant={config.tenant_id} created={created} updated={updated}")
        return {"created": created, "updated": updated, "errors": errors[:10]}

    except Exception as e:
        config.last_sync_status = "failed"
        config.last_sync_message = str(e)[:500]
        config.last_synced_at = datetime.utcnow()
        db.commit()
        logger.error(f"❌ Product sync failed: {e}")
        return {"created": 0, "updated": 0, "errors": [str(e)]}


# ═══════════════════════════════════════════════════════════════
# CSV FETCHER (with optional auth headers)
# ═══════════════════════════════════════════════════════════════

async def _fetch_csv(config: SyncConfig) -> str:
    """Fetch CSV content from external URL with optional auth."""
    # SSRF guard: block internal/private URLs
    parsed = urlparse(config.csv_url)
    hostname = parsed.hostname or ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", ""):
        raise ValueError(f"Blocked internal URL: {hostname}")
    if hostname.startswith(("10.", "192.168.")) or re.match(r"172\.(1[6-9]|2\d|3[01])\.", hostname):
        raise ValueError(f"Blocked private network URL: {hostname}")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only HTTP/HTTPS URLs are allowed, got: {parsed.scheme}")

    headers = {}
    if config.auth_header_name and config.auth_header_value:
        headers[config.auth_header_name] = config.auth_header_value

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(config.csv_url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        return response.text


# ═══════════════════════════════════════════════════════════════
# BACKGROUND SCHEDULER
# ═══════════════════════════════════════════════════════════════

async def run_scheduled_syncs(db: Session):
    """
    Find all active SyncConfigs that are due for sync and execute them.
    Called periodically by the background scheduler in main.py.
    """
    now = datetime.utcnow()

    # ★ Safety: reset stale "running" configs (stuck for >30 min = likely crashed)
    stale_running = db.query(SyncConfig).filter(
        SyncConfig.last_sync_status == "running",
        SyncConfig.last_synced_at != None,
    ).all()
    for stale in stale_running:
        if stale.last_synced_at and (now - stale.last_synced_at) > timedelta(minutes=30):
            stale.last_sync_status = "failed"
            stale.last_sync_message = "Reset: sync was stuck as running for >30 minutes"
            logger.warning(f"⚠️ Reset stale running sync config id={stale.id}")
    if stale_running:
        db.commit()

    configs = db.query(SyncConfig).filter(
        SyncConfig.is_active == True,
        SyncConfig.last_sync_status != "running",
    ).all()

    for config in configs:
        # Check if sync is due
        if config.last_synced_at:
            next_sync = config.last_synced_at + timedelta(minutes=config.sync_interval_minutes or 60)
            if now < next_sync:
                continue  # Not yet due

        logger.info(f"🔄 Running scheduled sync: id={config.id} type={config.sync_type} tenant={config.tenant_id}")

        try:
            if config.sync_type == "orders":
                await sync_orders(config, db)
            elif config.sync_type == "products":
                await sync_products(config, db)
            else:
                logger.warning(f"Unknown sync type: {config.sync_type}")
        except Exception as e:
            logger.error(f"Scheduled sync failed for config {config.id}: {e}")
            config.last_sync_status = "failed"
            config.last_sync_message = str(e)[:500]
            db.commit()
