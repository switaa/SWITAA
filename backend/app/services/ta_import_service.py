"""Import Tactical Arbitrage Product Search CSV into Marcus pipeline."""
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

logger = logging.getLogger("marcus.ta_import")

IP_RISK_BRANDS = [
    "hansgrohe", "grohe", "lego", "dyson", "nike", "adidas",
    "philips", "bosch", "siemens", "apple", "samsung", "sony",
    "bose", "dewalt", "makita", "stanley", "black+decker",
    "karcher", "kärcher", "miele", "tefal", "moulinex",
]

TA_COLUMN_MAP = {
    "ASIN": "asin",
    "Amazon Title": "title",
    "Brand": "brand",
    "Amazon Category": "category",
    "Amazon Buy Box Price": "buybox_price",
    "Sales Rank": "bsr",
    "Estimated Monthly Sales": "monthly_sales",
    "Reviews": "review_count",
    "Rating": "rating",
    "# Selling 'New'": "seller_count",
    "Competitive FBA Sellers": "_fba_sellers",
    "Amazon Sells and In Stock": "_amazon_stock_raw",
    "Buy Box": "buybox_seller",
    "Match Quality": "_match_quality",
    "Product Size": "_product_size",
    "Variations": "_variations",
}


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


def _clean_pct(val: str) -> float:
    if not val or val in ("N/A", "-", ""):
        return 0.0
    cleaned = val.replace("%", "").replace(",", ".").strip()
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


def _get_or_create_supplier(db: Session, source_name: str, user_id: uuid.UUID | None) -> Supplier:
    supplier = db.query(Supplier).filter(Supplier.name == source_name).first()
    if supplier:
        return supplier

    supplier = Supplier(
        name=source_name,
        access_type="WEB",
        host=f"{source_name.lower().replace(' ', '')}.fr",
        user_id=user_id,
    )
    db.add(supplier)
    db.flush()
    return supplier


def _parse_ta_row(row: dict[str, str]) -> dict[str, Any] | None:
    asin = row.get("ASIN", "").strip()
    if not asin or len(asin) != 10:
        return None

    match_quality = _safe_int(row.get("Match Quality", "")) or 0
    if match_quality < 50:
        return None

    source_price = _clean_currency(row.get("Price", ""))
    amazon_price = _clean_currency(row.get("Amazon Buy Box Price", ""))
    gross_profit = _clean_currency(row.get("Gross Profit", ""))
    gross_roi = _clean_pct(row.get("Gross ROI", ""))

    in_stock_raw = row.get("In Stock", "").strip().lower()
    amazon_stock_raw = row.get("Amazon Sells and In Stock", "").strip().lower()
    amazon_is_seller = "in stock" in amazon_stock_raw

    brand = row.get("Brand", "").strip()

    return {
        "asin": asin,
        "title": row.get("Amazon Title", "").strip()[:500] or row.get("Title", "").strip()[:500],
        "brand": brand[:255],
        "category": row.get("Amazon Category", "").strip()[:255],
        "buybox_price": amazon_price if amazon_price > 0 else None,
        "price": amazon_price if amazon_price > 0 else None,
        "bsr": _safe_int(row.get("Sales Rank", "")),
        "monthly_sales": _safe_int(row.get("Estimated Monthly Sales", "")),
        "review_count": _safe_int(row.get("Reviews", "")),
        "rating": _safe_float(row.get("Rating", "")),
        "seller_count": _safe_int(row.get("# Selling 'New'", "")),
        "buybox_seller": row.get("Buy Box", "").strip()[:255],
        "amazon_is_seller": amazon_is_seller,
        "brand_restricted": _is_ip_risk(brand),
        "source_price": source_price,
        "source_title": row.get("Title", "").strip()[:500],
        "source_url": row.get("Source URL", "").strip(),
        "source_in_stock": in_stock_raw == "yes",
        "ean": row.get("UPC / EAN", "").strip(),
        "match_quality": match_quality,
        "gross_profit": gross_profit,
        "gross_roi": gross_roi,
        "product_size": row.get("Product Size", "").strip(),
        "fba_sellers": _safe_int(row.get("Competitive FBA Sellers", "")),
        "variations": _safe_int(row.get("Variations", "")),
        "amazon_url": row.get("Amazon URL", "").strip(),
        "source_image": row.get("Product Image", "").strip(),
        "amazon_image": row.get("Amazon Image", "").strip(),
        "weight_lbs": _safe_float(row.get("Weight (lbs)", "")),
        "fulfillment_fee": _clean_currency(row.get("Fulfillment Fee", "")),
        "referral_pct": _clean_pct(row.get("Referral Percent", "")),
        "source_name": row.get("Source", "").strip(),
    }


def _upsert_product(
    db: Session, data: dict[str, Any], user_id: uuid.UUID | None
) -> Product:
    asin = data["asin"]
    existing = db.query(Product).filter(Product.asin == asin).first()

    product_fields = {
        "title": data.get("title", ""),
        "brand": data.get("brand", ""),
        "category": data.get("category", ""),
        "marketplace": "amazon_fr",
        "currency": "EUR",
        "source": "tactical_arbitrage",
        "amazon_is_seller": data.get("amazon_is_seller"),
        "buybox_seller": data.get("buybox_seller"),
        "brand_restricted": data.get("brand_restricted"),
    }

    numeric_fields = {
        "price": data.get("price"),
        "buybox_price": data.get("buybox_price"),
        "bsr": data.get("bsr"),
        "monthly_sales": data.get("monthly_sales"),
        "review_count": data.get("review_count"),
        "rating": data.get("rating"),
        "seller_count": data.get("seller_count"),
    }

    raw_data = {
        "ta_match_quality": data.get("match_quality"),
        "ta_gross_profit": data.get("gross_profit"),
        "ta_gross_roi": data.get("gross_roi"),
        "ta_product_size": data.get("product_size"),
        "ta_fba_sellers": data.get("fba_sellers"),
        "ta_variations": data.get("variations"),
        "ta_weight_lbs": data.get("weight_lbs"),
        "ta_fulfillment_fee": data.get("fulfillment_fee"),
        "ta_referral_pct": data.get("referral_pct"),
        "amazon_url": data.get("amazon_url"),
        "source_url": data.get("source_url"),
    }

    if existing:
        for k, v in product_fields.items():
            if v is not None:
                setattr(existing, k, v)
        for k, v in numeric_fields.items():
            if v is not None:
                setattr(existing, k, v)
        merged_raw = existing.raw_data or {}
        merged_raw.update(raw_data)
        existing.raw_data = merged_raw
        existing.image_url = data.get("amazon_image") or existing.image_url
        if user_id:
            existing.user_id = user_id
        return existing

    new_fields = {**product_fields, "asin": asin, "user_id": user_id}
    for k, v in numeric_fields.items():
        if v is not None:
            new_fields[k] = v
    new_fields["raw_data"] = raw_data
    new_fields["image_url"] = data.get("amazon_image", "")

    product = Product(**new_fields)
    db.add(product)
    db.flush()
    return product


def _create_supplier_product(
    db: Session, supplier: Supplier, product: Product, data: dict[str, Any]
) -> SupplierProduct:
    existing = (
        db.query(SupplierProduct)
        .filter(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.asin == data["asin"],
        )
        .first()
    )

    if existing:
        existing.price_ht = data.get("source_price", 0)
        existing.stock = 1 if data.get("source_in_stock") else 0
        existing.title = data.get("source_title", "")[:500]
        if data.get("ean"):
            existing.ean = data["ean"][:20]
        return existing

    sp = SupplierProduct(
        supplier_id=supplier.id,
        sku=data.get("ean") or data["asin"],
        asin=data["asin"],
        ean=data.get("ean", "")[:20] if data.get("ean") else None,
        title=data.get("source_title", "")[:500],
        price_ht=data.get("source_price", 0),
        stock=1 if data.get("source_in_stock") else 0,
    )
    db.add(sp)
    db.flush()
    return sp


def import_ta_csv(
    db: Session,
    csv_content: str | None = None,
    csv_path: str | Path | None = None,
    user_id: uuid.UUID | None = None,
    min_match_quality: int = 80,
    min_roi: float = 0.0,
    min_profit: float = 0.0,
) -> dict[str, Any]:
    """Import a Tactical Arbitrage Product Search CSV.

    Accepts either raw CSV content (from upload) or a file path.
    """
    if csv_content:
        reader_source = StringIO(csv_content)
    elif csv_path:
        p = Path(csv_path)
        if not p.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        reader_source = open(p, "r", encoding="utf-8-sig")
    else:
        raise ValueError("Provide csv_content or csv_path")

    stats: dict[str, Any] = {
        "total_rows": 0,
        "imported": 0,
        "skipped_match_quality": 0,
        "skipped_parse": 0,
        "skipped_filters": 0,
        "duplicates_merged": 0,
        "ip_risk_flagged": 0,
        "errors": 0,
        "products_created": 0,
        "products_updated": 0,
        "supplier_products_created": 0,
        "opportunities_created": 0,
    }

    try:
        reader = csv.DictReader(reader_source)
        seen_asins: set[str] = set()
        products_data: list[tuple[Product, SupplierProduct, dict[str, Any]]] = []

        source_names: set[str] = set()

        for row in reader:
            stats["total_rows"] += 1
            try:
                data = _parse_ta_row(row)
                if not data:
                    stats["skipped_parse"] += 1
                    continue

                if data["match_quality"] < min_match_quality:
                    stats["skipped_match_quality"] += 1
                    continue

                if min_roi > 0 and data["gross_roi"] < min_roi:
                    stats["skipped_filters"] += 1
                    continue

                if min_profit > 0 and data["gross_profit"] < min_profit:
                    stats["skipped_filters"] += 1
                    continue

                if data["asin"] in seen_asins:
                    stats["duplicates_merged"] += 1
                    continue
                seen_asins.add(data["asin"])

                if data.get("source_name"):
                    source_names.add(data["source_name"])

                existing_before = db.query(Product).filter(Product.asin == data["asin"]).first()
                product = _upsert_product(db, data, user_id)

                if existing_before:
                    stats["products_updated"] += 1
                else:
                    stats["products_created"] += 1

                if data.get("brand_restricted"):
                    stats["ip_risk_flagged"] += 1

                supplier_name = data.get("source_name") or "castorama.fr"
                supplier_name_clean = supplier_name.replace(".fr", "").replace(".com", "").capitalize()
                if not supplier_name_clean:
                    supplier_name_clean = "Castorama"

                supplier = _get_or_create_supplier(db, supplier_name_clean, user_id)
                sp = _create_supplier_product(db, supplier, product, data)
                if sp.id is None:
                    db.flush()
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

                cost_price = data.get("source_price", 0)
                score_result = score_product(product, cost_price=cost_price)

                selling_price = float(product.buybox_price or product.price or 0)
                fees = selling_price * 0.15
                ta_profit = data.get("gross_profit", 0)
                margin_abs = ta_profit if ta_profit > 0 else score_result.get("margin_abs", 0)
                margin_pct = (margin_abs / selling_price * 100) if selling_price > 0 else 0

                opp = Opportunity(
                    product_id=product.id,
                    supplier_product_id=sp.id,
                    user_id=user_id,
                    selling_price=selling_price,
                    cost_price=cost_price,
                    marketplace_fees=round(fees, 2),
                    shipping_cost=0,
                    margin_abs=round(margin_abs, 2),
                    margin_pct=round(margin_pct, 1),
                    score=score_result.get("score", 0),
                    margin_score=score_result.get("margin_score", 0),
                    competition_score=score_result.get("competition_score", 0),
                    demand_score=score_result.get("demand_score", 0),
                    bsr_score=score_result.get("bsr_score", 0),
                    decision=score_result.get("decision", "B_review"),
                    notes=f"TA import | ROI: {data.get('gross_roi', 0):.0f}% | Match: {data.get('match_quality', 0)}%",
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
        "TA import complete: %d/%d imported, %d opportunities, %d IP risk",
        stats["imported"],
        stats["total_rows"],
        stats["opportunities_created"],
        stats["ip_risk_flagged"],
    )
    return stats
