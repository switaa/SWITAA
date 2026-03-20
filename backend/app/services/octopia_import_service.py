"""Import OCTOPIA catalog CSV into Marcus pipeline.

Flexible column detection: auto-maps common column names to internal fields.
"""
from __future__ import annotations

import csv
import logging
import re
import uuid
from io import StringIO
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.supplier import Supplier, SupplierProduct
from app.services.scoring_service import score_product

logger = logging.getLogger("marcus.octopia_import")

COLUMN_ALIASES: dict[str, list[str]] = {
    "asin": ["asin", "amazon asin", "asin amazon", "code asin"],
    "ean": ["ean", "ean13", "ean 13", "gtin", "upc", "upc / ean", "barcode", "code barre", "code-barres"],
    "sku": ["sku", "sku octopia", "reference", "ref", "référence", "ref_octopia", "sku_octopia"],
    "title": ["title", "titre", "product title", "product name", "designation", "désignation", "libelle", "libellé", "nom produit", "nom"],
    "brand": ["brand", "marque", "brand name"],
    "category": ["category", "categorie", "catégorie", "product category", "amazon category", "type"],
    "price_buy": ["price_buy", "prix achat", "prix d'achat", "cost", "cost price", "prix ht", "prix_ht", "buy price", "purchase price", "pa ht", "pa_ht", "prix fournisseur"],
    "price_sell": ["price_sell", "prix vente", "prix de vente", "sell price", "selling price", "price", "prix", "prix ttc", "prix_ttc", "pv ttc", "pv_ttc", "amazon price", "prix amazon"],
    "stock": ["stock", "quantity", "quantite", "quantité", "qty", "stock disponible", "available stock"],
    "image_url": ["image", "image_url", "image url", "product image", "url image", "photo"],
    "description": ["description", "product description", "description produit"],
    "weight": ["weight", "poids", "weight_kg", "poids_kg"],
    "amazon_url": ["amazon url", "amazon_url", "url amazon", "lien amazon"],
}

IP_RISK_BRANDS = [
    "hansgrohe", "grohe", "lego", "dyson", "nike", "adidas",
    "philips", "bosch", "siemens", "apple", "samsung", "sony",
    "bose", "dewalt", "makita", "stanley", "black+decker",
    "karcher", "kärcher", "miele", "tefal", "moulinex",
]


def _clean_currency(val: str) -> float:
    if not val or val in ("N/A", "-", ""):
        return 0.0
    cleaned = re.sub(r"[^\d.,\-]", "", str(val))
    cleaned = cleaned.replace(",", ".")
    if cleaned.count(".") > 1:
        parts = cleaned.rsplit(".", 1)
        cleaned = parts[0].replace(".", "") + "." + parts[1]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val: str) -> int | None:
    if not val or val in ("N/A", "-", ""):
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _safe_float(val: str) -> float | None:
    if not val or val in ("N/A", "-", ""):
        return None
    cleaned = re.sub(r"[^\d.,\-]", "", str(val))
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _is_ip_risk(brand: str) -> bool:
    brand_lower = brand.lower().strip()
    return any(risk in brand_lower for risk in IP_RISK_BRANDS)


def _detect_columns(headers: list[str]) -> dict[str, str]:
    """Map CSV headers to internal field names via fuzzy alias matching."""
    mapping: dict[str, str] = {}
    normalized = {h: h.strip().lower() for h in headers}

    for field, aliases in COLUMN_ALIASES.items():
        for header, norm in normalized.items():
            if norm in aliases:
                mapping[field] = header
                break

    return mapping


def _get_or_create_supplier(db: Session, user_id: uuid.UUID | None) -> Supplier:
    supplier = db.query(Supplier).filter(Supplier.name == "OCTOPIA").first()
    if supplier:
        return supplier

    supplier = Supplier(
        name="OCTOPIA",
        access_type="API",
        host="octopia.com",
        user_id=user_id,
    )
    db.add(supplier)
    db.flush()
    return supplier


def _parse_row(row: dict[str, str], col_map: dict[str, str]) -> dict[str, Any] | None:
    asin_col = col_map.get("asin")
    ean_col = col_map.get("ean")
    sku_col = col_map.get("sku")

    asin = row.get(asin_col, "").strip() if asin_col else ""
    ean = row.get(ean_col, "").strip() if ean_col else ""
    sku = row.get(sku_col, "").strip() if sku_col else ""

    if not asin and not ean:
        return None

    if asin and len(asin) != 10:
        asin = ""

    if not asin:
        return None

    title_col = col_map.get("title")
    brand_col = col_map.get("brand")
    category_col = col_map.get("category")
    price_buy_col = col_map.get("price_buy")
    price_sell_col = col_map.get("price_sell")
    stock_col = col_map.get("stock")
    image_col = col_map.get("image_url")
    description_col = col_map.get("description")
    weight_col = col_map.get("weight")

    title = row.get(title_col, "").strip()[:500] if title_col else ""
    brand = row.get(brand_col, "").strip()[:255] if brand_col else ""
    category = row.get(category_col, "").strip()[:255] if category_col else ""
    price_buy = _clean_currency(row.get(price_buy_col, "")) if price_buy_col else 0.0
    price_sell = _clean_currency(row.get(price_sell_col, "")) if price_sell_col else 0.0
    stock = _safe_int(row.get(stock_col, "")) if stock_col else None
    image_url = row.get(image_col, "").strip() if image_col else ""
    description = row.get(description_col, "").strip()[:2000] if description_col else ""
    weight = _safe_float(row.get(weight_col, "")) if weight_col else None

    return {
        "asin": asin,
        "ean": ean,
        "sku": sku,
        "title": title,
        "brand": brand,
        "category": category,
        "price_buy": price_buy,
        "price_sell": price_sell,
        "stock": stock if stock is not None else 0,
        "image_url": image_url,
        "description": description,
        "weight": weight,
        "brand_restricted": _is_ip_risk(brand),
    }


def _upsert_product(
    db: Session, data: dict[str, Any], user_id: uuid.UUID | None
) -> tuple[Product, bool]:
    """Returns (product, is_new)."""
    asin = data["asin"]
    existing = db.query(Product).filter(Product.asin == asin).first()

    raw_data = {
        "octopia_sku": data.get("sku"),
        "octopia_ean": data.get("ean"),
        "octopia_stock": data.get("stock"),
        "octopia_description": data.get("description"),
        "octopia_weight": data.get("weight"),
    }

    if existing:
        if not existing.title and data.get("title"):
            existing.title = data["title"]
        if not existing.brand and data.get("brand"):
            existing.brand = data["brand"]
        if not existing.category and data.get("category"):
            existing.category = data["category"]
        if data.get("image_url") and not existing.image_url:
            existing.image_url = data["image_url"]
        if data.get("price_sell") and (not existing.price or float(existing.price) == 0):
            existing.price = data["price_sell"]
        existing.brand_restricted = data.get("brand_restricted") or existing.brand_restricted
        merged_raw = existing.raw_data or {}
        merged_raw.update(raw_data)
        existing.raw_data = merged_raw
        if user_id:
            existing.user_id = user_id
        return existing, False

    product = Product(
        asin=asin,
        title=data.get("title", ""),
        brand=data.get("brand", ""),
        category=data.get("category", ""),
        marketplace="amazon_fr",
        currency="EUR",
        source="octopia",
        price=data.get("price_sell") or 0,
        image_url=data.get("image_url", ""),
        brand_restricted=data.get("brand_restricted"),
        raw_data=raw_data,
        user_id=user_id,
    )
    db.add(product)
    db.flush()
    return product, True


def _create_supplier_product(
    db: Session, supplier: Supplier, product: Product, data: dict[str, Any]
) -> tuple[SupplierProduct, bool]:
    """Returns (supplier_product, is_new)."""
    existing = (
        db.query(SupplierProduct)
        .filter(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.asin == data["asin"],
        )
        .first()
    )

    if existing:
        existing.price_ht = data.get("price_buy") or existing.price_ht
        existing.stock = data.get("stock", 0)
        if data.get("title"):
            existing.title = data["title"][:500]
        if data.get("ean"):
            existing.ean = data["ean"][:20]
        return existing, False

    sp = SupplierProduct(
        supplier_id=supplier.id,
        sku=data.get("sku") or data.get("ean") or data["asin"],
        asin=data["asin"],
        ean=data.get("ean", "")[:20] if data.get("ean") else None,
        title=data.get("title", "")[:500],
        price_ht=data.get("price_buy") or 0,
        stock=data.get("stock", 0),
    )
    db.add(sp)
    db.flush()
    return sp, True


def import_octopia_csv(
    db: Session,
    csv_content: str | None = None,
    csv_path: str | Path | None = None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Import an OCTOPIA catalog CSV with automatic column detection."""
    if csv_content:
        reader_source = StringIO(csv_content)
    elif csv_path:
        p = Path(csv_path)
        if not p.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                reader_source = open(p, "r", encoding=enc)
                reader_source.readline()
                reader_source.seek(0)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Cannot decode CSV: {csv_path}")
    else:
        raise ValueError("Provide csv_content or csv_path")

    stats: dict[str, Any] = {
        "total_rows": 0,
        "imported": 0,
        "skipped_no_asin": 0,
        "skipped_parse": 0,
        "duplicates_merged": 0,
        "ip_risk_flagged": 0,
        "errors": 0,
        "products_created": 0,
        "products_updated": 0,
        "supplier_products_created": 0,
        "opportunities_created": 0,
        "columns_detected": {},
    }

    try:
        reader = csv.DictReader(reader_source)
        headers = reader.fieldnames or []
        col_map = _detect_columns(headers)
        stats["columns_detected"] = col_map
        stats["csv_headers"] = headers[:30]

        if not col_map.get("asin") and not col_map.get("ean"):
            logger.error("No ASIN or EAN column found. Headers: %s", headers)
            stats["error_message"] = f"No ASIN or EAN column found in headers: {headers[:20]}"
            return stats

        logger.info("Column mapping: %s", col_map)

        supplier = _get_or_create_supplier(db, user_id)
        seen_asins: set[str] = set()
        products_data: list[tuple[Product, SupplierProduct, dict[str, Any]]] = []

        for row in reader:
            stats["total_rows"] += 1
            try:
                data = _parse_row(row, col_map)
                if not data:
                    stats["skipped_parse"] += 1
                    continue

                if not data.get("asin"):
                    stats["skipped_no_asin"] += 1
                    continue

                if data["asin"] in seen_asins:
                    stats["duplicates_merged"] += 1
                    continue
                seen_asins.add(data["asin"])

                product, is_new = _upsert_product(db, data, user_id)
                if is_new:
                    stats["products_created"] += 1
                else:
                    stats["products_updated"] += 1

                if data.get("brand_restricted"):
                    stats["ip_risk_flagged"] += 1

                sp, sp_is_new = _create_supplier_product(db, supplier, product, data)
                if sp_is_new:
                    stats["supplier_products_created"] += 1

                products_data.append((product, sp, data))
                stats["imported"] += 1

            except Exception as e:
                stats["errors"] += 1
                logger.warning("Error on row %d: %s", stats["total_rows"], e)

        db.commit()

        for product, sp, data in products_data:
            db.refresh(product)

        for product, sp, data in products_data:
            try:
                existing_opp = (
                    db.query(Opportunity)
                    .filter(
                        Opportunity.product_id == product.id,
                        Opportunity.supplier_product_id == sp.id,
                    )
                    .first()
                )
                if existing_opp:
                    continue

                cost_price = data.get("price_buy") or 0
                score_result = score_product(product, cost_price=cost_price if cost_price > 0 else None)

                selling_price = float(product.price or 0)
                fees = selling_price * 0.15

                opp = Opportunity(
                    product_id=product.id,
                    supplier_product_id=sp.id,
                    user_id=user_id,
                    selling_price=selling_price,
                    cost_price=cost_price,
                    marketplace_fees=round(fees, 2),
                    shipping_cost=0,
                    margin_abs=score_result.get("margin_abs", 0),
                    margin_pct=score_result.get("margin_pct", 0),
                    score=score_result.get("score", 0),
                    margin_score=score_result.get("margin_score", 0),
                    competition_score=score_result.get("competition_score", 0),
                    demand_score=score_result.get("demand_score", 0),
                    bsr_score=score_result.get("bsr_score", 0),
                    decision=score_result.get("decision", "B_review"),
                    notes=f"OCTOPIA import | SKU: {data.get('sku', '')} | EAN: {data.get('ean', '')}",
                )
                db.add(opp)
                stats["opportunities_created"] += 1

            except Exception as e:
                stats["errors"] += 1
                logger.warning("Error creating opportunity for %s: %s", product.asin, e)

        db.commit()

    finally:
        if csv_path and hasattr(reader_source, "close"):
            reader_source.close()

    logger.info(
        "OCTOPIA import complete: %d/%d imported, %d products created, %d opportunities",
        stats["imported"],
        stats["total_rows"],
        stats["products_created"],
        stats["opportunities_created"],
    )
    return stats
