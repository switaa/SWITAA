"""Import Helium 10 Black Box CSV exports into Marcus pipeline."""
from __future__ import annotations

import csv
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product
from app.services.scoring_service import score_product

logger = logging.getLogger("marcus.csv_import")

NICHE_MAP = {
    "1": {"niche": "piscine", "sub_niche": "filtration"},
    "2": {"niche": "chauffage", "sub_niche": "pieces_detachees"},
    "3": {"niche": "electromenager", "sub_niche": "aspirateur"},
    "4": {"niche": "automobile", "sub_niche": "pieces_detachees"},
    "5": {"niche": "plomberie", "sub_niche": "robinet"},
    "6": {"niche": "jardinage", "sub_niche": "tuyau"},
    "7": {"niche": "electricite", "sub_niche": "interrupteur"},
    "8": {"niche": "outillage", "sub_niche": "foret"},
}

CSV_TO_PRODUCT = {
    "ASIN": "asin",
    "Title": "title",
    "Brand": "brand",
    "Category": "category",
    "Price": "price",
    "BSR": "bsr",
    "ASIN Sales": "monthly_sales",
    "Review Count": "review_count",
    "Reviews Rating": "rating",
    "Number of Active Sellers": "seller_count",
    "Image URL": "image_url",
}


def _safe_int(val: str) -> int | None:
    if not val or val in ("N/A", "", "-"):
        return None
    try:
        return int(float(val.replace(",", "")))
    except (ValueError, TypeError):
        return None


def _safe_float(val: str) -> float | None:
    if not val or val in ("N/A", "", "-"):
        return None
    try:
        return float(val.replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_csv_row(row: dict[str, str]) -> dict[str, Any] | None:
    """Parse a single CSV row into a product data dict."""
    asin = row.get("ASIN", "").strip()
    if not asin or len(asin) != 10:
        return None

    data: dict[str, Any] = {
        "asin": asin,
        "title": row.get("Title", "").strip()[:500],
        "brand": row.get("Brand", "").strip()[:255],
        "category": row.get("Category", "").strip()[:255],
        "price": _safe_float(row.get("Price", "")),
        "bsr": _safe_int(row.get("BSR", "")),
        "monthly_sales": _safe_int(row.get("ASIN Sales", "")),
        "review_count": _safe_int(row.get("Review Count", "")),
        "rating": _safe_float(row.get("Reviews Rating", "")),
        "seller_count": _safe_int(row.get("Number of Active Sellers", "")),
        "image_url": row.get("Image URL", "").strip(),
        "marketplace": "amazon_fr",
        "currency": "EUR",
        "source": "helium10_blackbox",
    }

    data["raw_data"] = {
        "url": row.get("URL", ""),
        "fulfillment": row.get("Fulfillment", ""),
        "subcategory": row.get("Subcategory", ""),
        "subcategory_bsr": _safe_int(row.get("Subcategory BSR", "")),
        "asin_revenue": _safe_float(row.get("ASIN Revenue", "")),
        "parent_level_sales": _safe_int(row.get("Parent Level Sales", "")),
        "price_trend_90d": _safe_float(row.get("Price Trend (90 days) (%)", "")),
        "sales_trend_90d": _safe_float(row.get("Sales Trend (90 days) (%)", "")),
        "seller": row.get("Seller", ""),
        "seller_country": row.get("Seller Country/Region", ""),
        "size_tier": row.get("Size Tier", ""),
        "weight": _safe_float(row.get("Weight", "")),
        "age_months": _safe_int(row.get("Age (Month)", "")),
        "variation_count": _safe_int(row.get("Variation Count", "")),
        "sales_to_reviews": _safe_float(row.get("Sales to Reviews", "")),
    }

    return data


def _upsert_product(
    db: Session, data: dict[str, Any], niche: str, sub_niche: str, user_id: uuid.UUID | None
) -> Product:
    """Create or update a product by ASIN."""
    asin = data["asin"]
    existing = db.query(Product).filter(Product.asin == asin).first()

    product_fields = {
        "asin": asin,
        "title": data.get("title", ""),
        "brand": data.get("brand", ""),
        "category": data.get("category", ""),
        "marketplace": data.get("marketplace", "amazon_fr"),
        "currency": data.get("currency", "EUR"),
        "source": data.get("source", "helium10_blackbox"),
        "niche": niche,
        "sub_niche": sub_niche,
        "user_id": user_id,
    }

    numeric_fields = {
        "price": data.get("price"),
        "bsr": data.get("bsr"),
        "monthly_sales": data.get("monthly_sales"),
        "review_count": data.get("review_count"),
        "rating": data.get("rating"),
        "seller_count": data.get("seller_count"),
    }

    if existing:
        for k, v in {**product_fields, **numeric_fields}.items():
            if v is not None and k != "asin":
                setattr(existing, k, v)
        existing.raw_data = data.get("raw_data")
        existing.image_url = data.get("image_url", "")
        return existing

    for k, v in numeric_fields.items():
        if v is not None:
            product_fields[k] = v

    product_fields["image_url"] = data.get("image_url", "")
    product_fields["raw_data"] = data.get("raw_data")

    product = Product(**product_fields)
    db.add(product)
    db.flush()
    return product


def import_single_csv(
    db: Session,
    csv_path: str | Path,
    niche: str,
    sub_niche: str,
    user_id: uuid.UUID | None = None,
    create_opportunities: bool = True,
) -> dict[str, Any]:
    """Import a single Helium 10 CSV file."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    stats = {"file": csv_path.name, "niche": niche, "total_rows": 0, "imported": 0, "skipped": 0, "errors": 0}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        products: list[Product] = []

        for row in reader:
            stats["total_rows"] += 1
            try:
                data = _parse_csv_row(row)
                if not data:
                    stats["skipped"] += 1
                    continue

                product = _upsert_product(db, data, niche, sub_niche, user_id)
                products.append(product)
                stats["imported"] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Error importing row {stats['total_rows']}: {e}")

        db.commit()

        if create_opportunities:
            for product in products:
                db.refresh(product)

            opp_count = 0
            for product in products:
                existing_opp = (
                    db.query(Opportunity)
                    .filter(Opportunity.product_id == product.id)
                    .first()
                )
                if existing_opp:
                    continue

                score_result = score_product(product, cost_price=None)
                opp = Opportunity(
                    product_id=product.id,
                    user_id=user_id,
                    selling_price=float(product.price or 0),
                    cost_price=0,
                    marketplace_fees=score_result.get("marketplace_fees", 0),
                    margin_abs=score_result.get("margin_abs", 0),
                    margin_pct=score_result.get("margin_pct", 0),
                    score=score_result.get("score", 0),
                    margin_score=score_result.get("margin_score", 0),
                    competition_score=score_result.get("competition_score", 0),
                    demand_score=score_result.get("demand_score", 0),
                    bsr_score=score_result.get("bsr_score", 0),
                    decision=score_result.get("decision", "B_review"),
                )
                db.add(opp)
                opp_count += 1

            db.commit()
            stats["opportunities_created"] = opp_count

    logger.info(f"Imported {csv_path.name}: {stats['imported']}/{stats['total_rows']} products")
    return stats


def import_all_csvs(
    db: Session,
    csv_dir: str | Path,
    user_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """Import all 8 Helium 10 CSV files from the CSV directory."""
    csv_dir = Path(csv_dir)
    all_stats = []

    for file_num in sorted(NICHE_MAP.keys()):
        niche_info = NICHE_MAP[file_num]
        pattern = f"FR_AMAZON_blackBoxProducts_{file_num}_*.csv"
        matches = list(csv_dir.glob(pattern))

        if not matches:
            logger.warning(f"No CSV found for niche {file_num} ({niche_info['niche']})")
            continue

        csv_file = matches[0]
        logger.info(f"Importing niche {file_num}: {niche_info['niche']}/{niche_info['sub_niche']} from {csv_file.name}")

        stats = import_single_csv(
            db=db,
            csv_path=csv_file,
            niche=niche_info["niche"],
            sub_niche=niche_info["sub_niche"],
            user_id=user_id,
        )
        all_stats.append(stats)

    total_imported = sum(s["imported"] for s in all_stats)
    total_opps = sum(s.get("opportunities_created", 0) for s in all_stats)
    logger.info(f"All CSVs imported: {total_imported} products, {total_opps} opportunities")

    return all_stats
