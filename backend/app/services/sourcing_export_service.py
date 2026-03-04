"""Export top products for sourcing tools (Tactical Arbitrage, PushLap, etc.)."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product
from app.services.profitability_service import calculate_profitability

logger = logging.getLogger("marcus.sourcing_export")


def export_top_products_csv(
    db: Session,
    min_score: float = 40.0,
    max_bsr: int = 100000,
    target_margin: float = 35.0,
    exclude_amazon_seller: bool = True,
    limit: int = 100,
) -> str:
    """Export top products as CSV for use with sourcing tools."""
    q = (
        db.query(Product, Opportunity.score, Opportunity.margin_score,
                 Opportunity.competition_score, Opportunity.demand_score)
        .join(Opportunity, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
        .filter(Product.price > 0)
    )

    if max_bsr:
        q = q.filter((Product.bsr <= max_bsr) | (Product.bsr.is_(None)))
    if exclude_amazon_seller:
        q = q.filter((Product.amazon_is_seller == False) | (Product.amazon_is_seller.is_(None)))

    rows = q.order_by(Opportunity.score.desc()).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ASIN", "Title", "Brand", "Niche", "Amazon URL",
        "Current Price (EUR)", "BuyBox Price (EUR)",
        "BSR", "Monthly Sales", "Seller Count", "Review Count", "Rating",
        "Amazon Is Seller", "Score",
        "Max Purchase Price (EUR)", "FBA Fees (EUR)", "Target Margin %",
        "Margin Score", "Competition Score", "Demand Score",
    ])

    for product, score, margin_s, comp_s, demand_s in rows:
        selling_price = float(product.buybox_price or product.price)
        raw = product.raw_data or {}
        weight = raw.get("weight")

        prof = calculate_profitability(
            selling_price=selling_price,
            cost_price=0,
            weight_kg=float(weight) if weight else None,
        )

        max_cost = prof["break_even_cost"] * (1 - target_margin / 100)

        writer.writerow([
            product.asin,
            product.title,
            product.brand,
            product.niche or "",
            f"https://www.amazon.fr/dp/{product.asin}",
            round(float(product.price), 2),
            round(float(product.buybox_price), 2) if product.buybox_price else "",
            product.bsr or "",
            product.monthly_sales or "",
            product.seller_count or "",
            product.review_count or "",
            round(float(product.rating), 2) if product.rating else "",
            "Yes" if product.amazon_is_seller else "No" if product.amazon_is_seller is False else "",
            round(float(score), 1),
            round(max_cost, 2),
            round(prof["total_fees"], 2),
            target_margin,
            round(float(margin_s or 0), 1),
            round(float(comp_s or 0), 1),
            round(float(demand_s or 0), 1),
        ])

    return output.getvalue()


def get_sourcing_summary(
    db: Session,
    min_score: float = 40.0,
    max_bsr: int = 100000,
    exclude_amazon_seller: bool = True,
) -> dict[str, Any]:
    """Summarize products ready for sourcing."""
    q = (
        db.query(Product, Opportunity.score)
        .join(Opportunity, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
        .filter(Product.price > 0)
    )

    if max_bsr:
        q = q.filter((Product.bsr <= max_bsr) | (Product.bsr.is_(None)))
    if exclude_amazon_seller:
        q = q.filter((Product.amazon_is_seller == False) | (Product.amazon_is_seller.is_(None)))

    rows = q.all()

    if not rows:
        return {"total": 0, "niches": {}, "avg_price": 0, "avg_score": 0}

    niche_counts: dict[str, int] = {}
    total_price = 0.0
    total_score = 0.0
    for product, score in rows:
        n = product.niche or "autre"
        niche_counts[n] = niche_counts.get(n, 0) + 1
        total_price += float(product.price)
        total_score += float(score)

    return {
        "total": len(rows),
        "niches": niche_counts,
        "avg_price": round(total_price / len(rows), 2),
        "avg_score": round(total_score / len(rows), 1),
    }
