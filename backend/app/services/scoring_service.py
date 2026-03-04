"""Product scoring and opportunity analysis."""
from __future__ import annotations

import logging
from typing import Any

from app.models.product import Product

logger = logging.getLogger("marcus.scoring")

WEIGHTS = {"margin": 0.35, "competition": 0.25, "demand": 0.25, "bsr": 0.15}
THRESHOLDS = {
    "min_margin_pct": 20,
    "max_sellers": 50,
    "min_monthly_sales": 100,
    "max_bsr": 100_000,
}


def score_product(product: Product, cost_price: float | None = None) -> dict[str, Any]:
    margin_s = _score_margin(product, cost_price)
    competition_s = _score_competition(product)
    demand_s = _score_demand(product)
    bsr_s = _score_bsr(product)

    total = (
        margin_s * WEIGHTS["margin"]
        + competition_s * WEIGHTS["competition"]
        + demand_s * WEIGHTS["demand"]
        + bsr_s * WEIGHTS["bsr"]
    )

    margin_abs, margin_pct = 0.0, 0.0
    fees = float(product.price or 0) * 0.15
    if cost_price and product.price:
        margin_abs = float(product.price) - fees - cost_price
        margin_pct = (margin_abs / float(product.price)) * 100 if float(product.price) > 0 else 0

    if total >= 70:
        decision = "A_launch"
    elif total >= 40:
        decision = "B_review"
    else:
        decision = "C_drop"

    return {
        "score": round(total, 2),
        "margin_score": round(margin_s, 2),
        "competition_score": round(competition_s, 2),
        "demand_score": round(demand_s, 2),
        "bsr_score": round(bsr_s, 2),
        "margin_abs": round(margin_abs, 2),
        "margin_pct": round(margin_pct, 1),
        "marketplace_fees": round(fees, 2),
        "decision": decision,
    }


def _score_margin(product: Product, cost_price: float | None) -> float:
    if not cost_price or not product.price or float(product.price) <= 0:
        return 50.0
    fees = float(product.price) * 0.15
    net = float(product.price) - fees - cost_price
    pct = (net / float(product.price)) * 100
    min_m = THRESHOLDS["min_margin_pct"]
    if pct >= min_m * 2:
        return 100.0
    if pct >= min_m:
        return 50 + (pct - min_m) / min_m * 50
    if pct > 0:
        return pct / min_m * 50
    return 0.0


def _score_competition(product: Product) -> float:
    sellers = product.seller_count
    reviews = product.review_count
    score = 50.0
    if sellers is not None:
        if sellers <= 5:
            score = 100.0
        elif sellers <= THRESHOLDS["max_sellers"]:
            score = 100 - (sellers / THRESHOLDS["max_sellers"]) * 60
        else:
            score = max(0, 40 - (sellers - THRESHOLDS["max_sellers"]) / 10)
    if reviews is not None:
        if reviews < 50:
            score = min(100, score + 20)
        elif reviews > 1000:
            score = max(0, score - 15)
    return min(100, max(0, score))


def _score_demand(product: Product) -> float:
    sales = product.monthly_sales
    min_s = THRESHOLDS["min_monthly_sales"]
    if sales is None:
        return 50.0
    if sales >= min_s * 10:
        return 100.0
    if sales >= min_s:
        return 50 + (sales - min_s) / (min_s * 9) * 50
    if sales > 0:
        return sales / min_s * 50
    return 0.0


def _score_bsr(product: Product) -> float:
    bsr = product.bsr
    max_b = THRESHOLDS["max_bsr"]
    if bsr is None:
        return 50.0
    if bsr <= 1000:
        return 100.0
    if bsr <= max_b:
        return 100 - (bsr / max_b) * 60
    return max(0, 40 - (bsr - max_b) / max_b * 40)
