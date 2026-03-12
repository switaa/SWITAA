"""Auto-generate Amazon listings from product data using clone or AI strategies."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from sqlalchemy import or_

from app.core.config import get_settings
from app.models.listing import Listing
from app.models.opportunity import Opportunity
from app.models.product import Product

logger = logging.getLogger("marcus.listing_generator")

SYSTEM_PROMPT = """\
Tu es un expert en création de listings Amazon FR pour des pièces techniques de remplacement \
(plomberie, électricité, bricolage, chauffage). Tu optimises les titres, bullet points et \
descriptions pour maximiser la visibilité et les conversions sur Amazon.fr.

Règles :
- Titre : max 200 caractères, inclure marque + nom produit + caractéristiques clés + référence
- 5 bullet points : avantages concrets, compatibilité, dimensions/specs, qualité, livraison
- Description : 1000 caractères max, paragraphes courts, mots-clés naturels
- Search terms : mots-clés supplémentaires séparés par des espaces, 250 caractères max
- Langue : français courant et professionnel
- Ne jamais inventer de spécifications techniques non confirmées
"""


async def generate_listing_clone(
    product: Product, db: Session
) -> dict[str, Any]:
    """Clone strategy: fetch existing Amazon listing data via SP-API and adapt it."""
    from app.services.spapi_client import SPAPIClient

    spapi = SPAPIClient()
    catalog_data = await spapi.get_catalog_item(product.asin)

    title = product.title or ""
    bullets: list[str] = []
    description = ""

    if catalog_data:
        summaries = catalog_data.get("summaries", [])
        if summaries:
            summary = summaries[0]
            title = summary.get("itemName", title)

        attrs = catalog_data.get("attributes", {})
        if attrs:
            bp = attrs.get("bullet_point", [])
            bullets = [b.get("value", "") for b in bp if b.get("value")]
            desc_list = attrs.get("product_description", [])
            if desc_list:
                description = desc_list[0].get("value", "")

    if not bullets:
        bullets = _generate_default_bullets(product)

    return {
        "title": title[:500],
        "bullets": bullets[:5],
        "description": description[:2000],
        "search_terms": _build_search_terms(product),
        "brand_name": product.brand or "",
        "strategy": "clone_best",
    }


async def generate_listing_ai(
    product: Product, db: Session
) -> dict[str, Any]:
    """AI strategy: use OpenAI to generate optimized listing content."""
    settings = get_settings()

    if not settings.OPENAI_API_KEY:
        logger.warning("No OpenAI API key, falling back to clone strategy")
        return await generate_listing_clone(product, db)

    raw = product.raw_data or {}
    product_info = (
        f"ASIN: {product.asin}\n"
        f"Titre actuel: {product.title}\n"
        f"Marque: {product.brand}\n"
        f"Catégorie: {product.category}\n"
        f"Prix: {product.price}€\n"
        f"Taille produit: {raw.get('ta_product_size', 'N/A')}\n"
        f"Ventes mensuelles: {product.monthly_sales}\n"
        f"Nb vendeurs: {product.seller_count}\n"
        f"Avis: {product.review_count} ({product.rating}/5)\n"
    )

    user_prompt = (
        f"Génère un listing Amazon FR optimisé pour ce produit :\n\n"
        f"{product_info}\n\n"
        f"Réponds EXACTEMENT au format suivant (une section par ligne) :\n"
        f"TITRE: [titre optimisé]\n"
        f"BULLET1: [premier point]\n"
        f"BULLET2: [deuxième point]\n"
        f"BULLET3: [troisième point]\n"
        f"BULLET4: [quatrième point]\n"
        f"BULLET5: [cinquième point]\n"
        f"DESCRIPTION: [description complète]\n"
        f"SEARCH_TERMS: [mots-clés supplémentaires]"
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                },
            )

        if resp.status_code != 200:
            logger.error("OpenAI error %d: %s", resp.status_code, resp.text[:300])
            return await generate_listing_clone(product, db)

        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_ai_response(content, product)

    except Exception as e:
        logger.error("AI listing generation error: %s", e)
        return await generate_listing_clone(product, db)


def _parse_ai_response(content: str, product: Product) -> dict[str, Any]:
    lines = content.strip().split("\n")
    result: dict[str, Any] = {
        "title": product.title or "",
        "bullets": [],
        "description": "",
        "search_terms": "",
        "brand_name": product.brand or "",
        "strategy": "ai_optimize",
    }

    for line in lines:
        line = line.strip()
        if line.upper().startswith("TITRE:"):
            result["title"] = line.split(":", 1)[1].strip()[:500]
        elif line.upper().startswith("BULLET"):
            bullet_text = line.split(":", 1)[1].strip() if ":" in line else ""
            if bullet_text:
                result["bullets"].append(bullet_text)
        elif line.upper().startswith("DESCRIPTION:"):
            result["description"] = line.split(":", 1)[1].strip()[:2000]
        elif line.upper().startswith("SEARCH_TERMS:"):
            result["search_terms"] = line.split(":", 1)[1].strip()[:250]

    if not result["bullets"]:
        result["bullets"] = _generate_default_bullets(product)

    return result


def _generate_default_bullets(product: Product) -> list[str]:
    bullets = []
    if product.brand:
        bullets.append(f"Produit de marque {product.brand} - Qualité garantie")
    if product.category:
        bullets.append(f"Catégorie : {product.category}")
    raw = product.raw_data or {}
    size = raw.get("ta_product_size", "")
    if size:
        bullets.append(f"Taille : {size}")
    bullets.append("Livraison rapide et soignée")
    bullets.append("Satisfait ou remboursé sous 30 jours")
    return bullets[:5]


def _build_search_terms(product: Product) -> str:
    terms: list[str] = []
    if product.brand:
        terms.append(product.brand.lower())
    if product.category:
        for word in product.category.lower().split():
            if len(word) > 3 and word not in terms:
                terms.append(word)
    if product.title:
        for word in product.title.lower().split():
            if len(word) > 4 and word not in terms:
                terms.append(word)
    return " ".join(terms[:40])[:250]


async def generate_single_listing(
    db: Session,
    product_id: str,
    user_id: str,
    strategy: str = "clone_best",
) -> Listing:
    """Generate a listing for a single product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product not found: {product_id}")

    if strategy == "ai_optimize":
        data = await generate_listing_ai(product, db)
    else:
        data = await generate_listing_clone(product, db)

    existing = (
        db.query(Listing)
        .filter(Listing.product_id == product.id, Listing.marketplace == "amazon_fr")
        .first()
    )

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        existing.status = "auto_generated"
        db.commit()
        db.refresh(existing)
        return existing

    listing = Listing(
        product_id=product.id,
        marketplace="amazon_fr",
        status="auto_generated",
        user_id=user_id,
        **data,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


async def generate_batch_listings(
    db: Session,
    user_id: str,
    strategy: str = "clone_best",
    min_score: float = 70.0,
    decision: str | None = "A_launch",
    limit: int = 50,
) -> dict[str, Any]:
    """Generate listings for top-scored opportunities that don't have one yet."""
    query = (
        db.query(Opportunity)
        .join(Product, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
    )

    if decision:
        query = query.filter(Opportunity.decision == decision)

    query = query.filter(or_(Product.brand_restricted == False, Product.brand_restricted.is_(None)))

    opportunities = query.order_by(Opportunity.score.desc()).limit(limit).all()

    stats = {"total_opportunities": len(opportunities), "listings_created": 0, "listings_updated": 0, "errors": 0}

    for opp in opportunities:
        try:
            product = opp.product
            if not product:
                continue

            existing = (
                db.query(Listing)
                .filter(Listing.product_id == product.id, Listing.marketplace == "amazon_fr")
                .first()
            )

            if existing and existing.status in ("published", "live"):
                continue

            if strategy == "ai_optimize":
                data = await generate_listing_ai(product, db)
            else:
                data = await generate_listing_clone(product, db)

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                existing.status = "auto_generated"
                stats["listings_updated"] += 1
            else:
                listing = Listing(
                    product_id=product.id,
                    marketplace="amazon_fr",
                    status="auto_generated",
                    user_id=user_id,
                    **data,
                )
                db.add(listing)
                stats["listings_created"] += 1

        except Exception as e:
            stats["errors"] += 1
            logger.warning("Error generating listing for product %s: %s", opp.product_id, e)

    db.commit()
    logger.info(
        "Batch listing generation: %d created, %d updated, %d errors",
        stats["listings_created"],
        stats["listings_updated"],
        stats["errors"],
    )
    return stats
