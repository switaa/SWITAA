"""FBA profitability calculator for Amazon FR products."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product

logger = logging.getLogger("marcus.profitability")

REFERRAL_FEE_PCT = 0.15
CLOSING_FEE = 0.0

FBA_FEES_FR = {
    "small_envelope": {"max_weight": 0.08, "max_longest": 20, "fee": 2.09},
    "standard_envelope": {"max_weight": 0.46, "max_longest": 33, "fee": 2.74},
    "large_envelope": {"max_weight": 0.96, "max_longest": 33, "fee": 3.45},
    "small_parcel": {"max_weight": 0.15, "max_longest": 35, "fee": 3.07},
    "standard_parcel_1": {"max_weight": 0.4, "max_longest": 45, "fee": 4.07},
    "standard_parcel_2": {"max_weight": 0.9, "max_longest": 45, "fee": 4.44},
    "standard_parcel_3": {"max_weight": 1.4, "max_longest": 45, "fee": 5.11},
    "standard_parcel_4": {"max_weight": 1.9, "max_longest": 45, "fee": 5.33},
    "standard_parcel_5": {"max_weight": 3.9, "max_longest": 45, "fee": 5.82},
    "standard_parcel_6": {"max_weight": 7.9, "max_longest": 61, "fee": 6.16},
    "standard_parcel_7": {"max_weight": 11.9, "max_longest": 61, "fee": 6.75},
    "small_oversize": {"max_weight": 1.76, "max_longest": 61, "fee": 6.44},
    "standard_oversize": {"max_weight": 29.76, "max_longest": 120, "fee": 8.80},
    "large_oversize": {"max_weight": 31.5, "max_longest": 175, "fee": 14.32},
}


def estimate_fba_fee(weight_kg: float | None, longest_side_cm: float | None) -> float:
    """Estimate FBA fulfillment fee based on weight and longest dimension."""
    w = weight_kg or 0.5
    l = longest_side_cm or 30.0

    for tier in FBA_FEES_FR.values():
        if w <= tier["max_weight"] and l <= tier["max_longest"]:
            return tier["fee"]
    return 8.80


def calculate_profitability(
    selling_price: float,
    cost_price: float,
    weight_kg: float | None = None,
    longest_side_cm: float | None = None,
    shipping_to_fba: float = 1.50,
) -> dict[str, Any]:
    """Calculate full profitability breakdown for a product."""
    if selling_price <= 0:
        return {
            "selling_price": 0, "cost_price": cost_price,
            "referral_fee": 0, "fba_fee": 0, "shipping_to_fba": 0,
            "total_fees": 0, "net_profit": 0, "margin_pct": 0,
            "roi": 0, "break_even_cost": 0,
        }

    referral_fee = selling_price * REFERRAL_FEE_PCT
    fba_fee = estimate_fba_fee(weight_kg, longest_side_cm)
    total_fees = referral_fee + fba_fee + shipping_to_fba + CLOSING_FEE

    net_profit = selling_price - total_fees - cost_price
    margin_pct = (net_profit / selling_price * 100) if selling_price > 0 else 0
    roi = (net_profit / cost_price * 100) if cost_price > 0 else 0
    break_even_cost = selling_price - total_fees

    return {
        "selling_price": round(selling_price, 2),
        "cost_price": round(cost_price, 2),
        "referral_fee": round(referral_fee, 2),
        "fba_fee": round(fba_fee, 2),
        "shipping_to_fba": round(shipping_to_fba, 2),
        "total_fees": round(total_fees, 2),
        "net_profit": round(net_profit, 2),
        "margin_pct": round(margin_pct, 1),
        "roi": round(roi, 1),
        "break_even_cost": round(break_even_cost, 2),
    }


def enrich_opportunities_with_profitability(
    db: Session,
    target_margin_pct: float = 35.0,
) -> dict[str, Any]:
    """Recalculate profitability for all opportunities using FBA fee model.

    Sets cost_price to break-even minus target margin to show what the
    max purchase price should be for the target margin.
    """
    opportunities = (
        db.query(Opportunity)
        .join(Product, Opportunity.product_id == Product.id)
        .all()
    )

    updated = 0
    for opp in opportunities:
        product = opp.product
        if not product or float(product.price or 0) <= 0:
            continue

        selling_price = float(product.buybox_price or product.price)
        raw = product.raw_data or {}

        weight = raw.get("weight") or raw.get("spapi", {}).get("weight")
        longest = None
        for dim_key in ("length", "width", "height"):
            val = raw.get(dim_key)
            if val and (longest is None or val > longest):
                longest = val

        weight_f = float(weight) if weight else None
        longest_f = float(longest) if longest else None

        prof = calculate_profitability(
            selling_price=selling_price,
            cost_price=0,
            weight_kg=weight_f,
            longest_side_cm=longest_f,
        )

        max_cost = prof["break_even_cost"] * (1 - target_margin_pct / 100)

        opp.selling_price = selling_price
        opp.marketplace_fees = prof["total_fees"]
        opp.cost_price = round(max_cost, 2)
        opp.margin_abs = round(selling_price - prof["total_fees"] - max_cost, 2)
        opp.margin_pct = round(target_margin_pct, 1)
        opp.shipping_cost = prof["shipping_to_fba"]

        updated += 1

    db.commit()
    logger.info("Profitability updated for %d opportunities", updated)
    return {"updated": updated, "target_margin_pct": target_margin_pct}
