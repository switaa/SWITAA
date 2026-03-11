"""Web sourcing service — searches French retail/wholesale sites for product matches.

Strategies:
1. CSV price list upload + auto-match by ASIN/EAN
2. Web search on French e-commerce sites (ManoMano, CDiscount, Leroy Merlin)
3. Google Shopping search via httpx
"""
from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import httpx
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sourcing import SourcingResult, SourcingSearch
from app.services.profitability_service import calculate_profitability

logger = logging.getLogger("marcus.web_sourcing")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

FRENCH_SOURCES = [
    {"name": "ManoMano", "search_url": "https://www.manomano.fr/recherche/{query}", "type": "diy"},
    {"name": "CDiscount", "search_url": "https://www.cdiscount.com/search/10/{query}.html", "type": "general"},
    {"name": "Leroy Merlin", "search_url": "https://www.leroymerlin.fr/search?q={query}", "type": "diy"},
    {"name": "Brico Depot", "search_url": "https://www.bricodepot.fr/recherche?q={query}", "type": "diy"},
]

TVA_RATE = 0.20


def _extract_prices_from_html(html: str) -> list[dict[str, Any]]:
    """Extract prices from HTML using regex patterns common across e-commerce sites."""
    results = []
    price_patterns = [
        r'"price"\s*:\s*"?([\d]+[.,]?\d*)"?',
        r'data-price="([\d]+[.,]?\d*)"',
        r'class="[^"]*price[^"]*"[^>]*>([\d]+[.,]?\d*)\s*[€]',
        r'([\d]+[.,]\d{2})\s*€',
    ]
    for pattern in price_patterns:
        matches = re.findall(pattern, html[:50000])
        for m in matches:
            try:
                price = float(m.replace(",", "."))
                if 1.0 < price < 5000.0:
                    results.append({"price": price})
            except ValueError:
                continue
        if results:
            break
    return results


async def search_product_on_web(
    product_title: str,
    asin: str,
    max_sources: int = 5,
) -> list[dict[str, Any]]:
    """Search for a product across French e-commerce sites."""
    query = re.sub(r'[^\w\s-]', '', product_title[:80]).strip()
    if not query:
        return []

    found: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for source in FRENCH_SOURCES[:max_sources]:
            try:
                url = source["search_url"].format(query=quote_plus(query))
                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                if resp.status_code == 200:
                    prices = _extract_prices_from_html(resp.text)
                    if prices:
                        found.append({
                            "source_name": source["name"],
                            "source_url": url,
                            "source_price": prices[0]["price"],
                            "source_title": query,
                            "match_type": "title",
                            "match_confidence": 0.6,
                        })
            except Exception as e:
                logger.debug("Search error on %s: %s", source["name"], e)
                continue

    return found


def _calculate_sourcing_profitability(
    source_price_ttc: float,
    amazon_price: float,
    mode: str = "fbm",
) -> dict[str, Any]:
    """Calculate profitability for a sourcing opportunity."""
    source_price_ht = source_price_ttc / (1 + TVA_RATE)
    prof = calculate_profitability(
        selling_price=amazon_price,
        cost_price=source_price_ht,
        mode=mode,
    )
    return {
        "source_price_ht": round(source_price_ht, 2),
        "referral_fee": prof["referral_fee"],
        "fulfillment_cost": prof["fulfillment_fee"] + prof["shipping_cost"],
        "net_profit": prof["net_profit"],
        "margin_pct": prof["margin_pct"],
        "roi_pct": prof["roi"],
    }


async def run_web_sourcing(
    db: Session,
    user_id: str | None = None,
    min_score: float = 30,
    max_products: int = 50,
    mode: str = "fbm",
) -> dict[str, Any]:
    """Run a web sourcing search for top Marcus products."""
    search = SourcingSearch(
        name=f"Web Search {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        search_type="web",
        status="running",
        user_id=uuid.UUID(user_id) if user_id else None,
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    from app.models.opportunity import Opportunity
    products = (
        db.query(Product)
        .join(Opportunity, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
        .filter(Product.price > 15)
        .filter(Product.price < 200)
        .order_by(Opportunity.score.desc())
        .limit(max_products)
        .all()
    )

    search.total_products = len(products)
    db.commit()

    matches_found = 0
    profitable = 0

    for i, product in enumerate(products):
        search.products_checked = i + 1
        db.commit()

        try:
            results = await search_product_on_web(product.title, product.asin)
        except Exception as e:
            logger.error("Error searching %s: %s", product.asin, e)
            continue

        amazon_price = float(product.buybox_price or product.price)

        for r in results:
            source_price = r["source_price"]
            prof = _calculate_sourcing_profitability(source_price, amazon_price, mode)

            result = SourcingResult(
                search_id=search.id,
                product_id=product.id,
                asin=product.asin,
                source_name=r["source_name"],
                source_url=r["source_url"],
                source_price=source_price,
                source_price_ht=prof["source_price_ht"],
                source_title=r.get("source_title", ""),
                amazon_price=amazon_price,
                referral_fee=prof["referral_fee"],
                fulfillment_cost=prof["fulfillment_cost"],
                net_profit=prof["net_profit"],
                margin_pct=prof["margin_pct"],
                roi_pct=prof["roi_pct"],
                match_type=r.get("match_type", "title"),
                match_confidence=r.get("match_confidence", 0.5),
            )
            db.add(result)
            matches_found += 1
            if prof["net_profit"] > 0:
                profitable += 1

    search.status = "completed"
    search.matches_found = matches_found
    search.profitable_count = profitable
    search.completed_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(
        "Web sourcing completed: %d products, %d matches, %d profitable",
        len(products), matches_found, profitable,
    )
    return {
        "search_id": str(search.id),
        "total_products": len(products),
        "matches_found": matches_found,
        "profitable_count": profitable,
    }


def import_csv_pricelist(
    db: Session,
    csv_content: str,
    source_name: str = "CSV Import",
    delimiter: str = ";",
    mode: str = "fbm",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Import a supplier CSV price list and auto-match with Marcus products.

    Expected CSV columns (flexible mapping):
    - asin OR ean OR reference
    - price OR prix OR price_ht OR prix_ht
    - title OR designation (optional)
    - stock OR quantity (optional)
    """
    search = SourcingSearch(
        name=f"CSV: {source_name}",
        search_type="csv",
        status="running",
        user_id=uuid.UUID(user_id) if user_id else None,
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
    if not reader.fieldnames:
        search.status = "failed"
        search.error_message = "CSV vide ou format invalide"
        db.commit()
        return {"error": "CSV vide ou format invalide"}

    fields_lower = {f.lower().strip(): f for f in reader.fieldnames}

    asin_col = fields_lower.get("asin") or fields_lower.get("ean") or fields_lower.get("reference")
    price_col = (
        fields_lower.get("price") or fields_lower.get("prix")
        or fields_lower.get("price_ht") or fields_lower.get("prix_ht")
        or fields_lower.get("price_ttc") or fields_lower.get("prix_ttc")
    )
    title_col = fields_lower.get("title") or fields_lower.get("designation") or fields_lower.get("name")
    stock_col = fields_lower.get("stock") or fields_lower.get("quantity") or fields_lower.get("qty")

    is_ht = any(k in fields_lower for k in ("price_ht", "prix_ht"))

    if not price_col:
        search.status = "failed"
        search.error_message = "Colonne prix introuvable dans le CSV"
        db.commit()
        return {"error": "Colonne prix introuvable"}

    rows = list(reader)
    search.total_products = len(rows)
    db.commit()

    matches_found = 0
    profitable = 0
    checked = 0

    all_products = {p.asin: p for p in db.query(Product).all()}

    for row in rows:
        checked += 1
        identifier = row.get(asin_col, "").strip() if asin_col else ""
        if not identifier:
            continue

        price_str = row.get(price_col, "0").replace(",", ".").strip()
        try:
            price_val = float(price_str)
        except ValueError:
            continue

        if price_val <= 0:
            continue

        product = all_products.get(identifier)
        if not product:
            for p in all_products.values():
                raw = p.raw_data or {}
                if raw.get("ean") == identifier or raw.get("upc") == identifier:
                    product = p
                    break

        if not product:
            continue

        amazon_price = float(product.buybox_price or product.price)
        if amazon_price <= 0:
            continue

        if is_ht:
            source_price_ttc = price_val * (1 + TVA_RATE)
            source_price_ht = price_val
        else:
            source_price_ttc = price_val
            source_price_ht = price_val / (1 + TVA_RATE)

        prof = _calculate_sourcing_profitability(source_price_ttc, amazon_price, mode)
        source_title = row.get(title_col, "").strip() if title_col else ""

        result = SourcingResult(
            search_id=search.id,
            product_id=product.id,
            asin=product.asin,
            source_name=source_name,
            source_price=source_price_ttc,
            source_price_ht=round(source_price_ht, 2),
            source_title=source_title,
            source_in_stock=int(row.get(stock_col, "0") or "0") > 0 if stock_col else None,
            amazon_price=amazon_price,
            referral_fee=prof["referral_fee"],
            fulfillment_cost=prof["fulfillment_cost"],
            net_profit=prof["net_profit"],
            margin_pct=prof["margin_pct"],
            roi_pct=prof["roi_pct"],
            match_type="asin" if product.asin == identifier else "ean",
            match_confidence=1.0,
        )
        db.add(result)
        matches_found += 1
        if prof["net_profit"] > 0:
            profitable += 1

    search.status = "completed"
    search.products_checked = checked
    search.matches_found = matches_found
    search.profitable_count = profitable
    search.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "search_id": str(search.id),
        "total_rows": len(rows),
        "matches_found": matches_found,
        "profitable_count": profitable,
    }
