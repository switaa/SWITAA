"""Research pipeline orchestrator - runs search campaigns through 4 phases."""
from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.search_campaign import SearchCampaign, SearchResult

logger = logging.getLogger("marcus.research_pipeline")

NICHE_KEYWORDS = {
    "piscine_filtration": {
        "niche": "piscine",
        "sub_niche": "filtration",
        "keywords": [
            "vanne 6 voies piscine",
            "vanne multivoie filtre sable",
            "crepine filtre piscine",
            "manometre filtre piscine",
            "joint filtre sable piscine",
            "bouchon hivernage piscine",
            "verre filtrant piscine",
            "sable filtration piscine",
            "collecteur filtre sable",
            "purge air filtre piscine",
            "coude raccord filtre piscine",
            "flexible raccord piscine",
            "bride filtre piscine",
            "joint torique filtre piscine",
            "diffuseur filtre sable",
        ],
    },
    "piscine_pompe": {
        "niche": "piscine",
        "sub_niche": "pompe",
        "keywords": [
            "couvercle prefiltre pompe piscine",
            "joint pompe piscine",
            "turbine pompe piscine",
            "panier prefiltre piscine",
            "garniture mecanique pompe piscine",
            "condensateur pompe piscine",
            "joint diffuseur pompe piscine",
            "raccord pompe piscine",
            "coude aspiration piscine",
            "clapet anti retour piscine",
            "vanne arret piscine",
            "bouchon purge pompe piscine",
            "joint couvercle pompe piscine",
            "flasque pompe piscine",
            "roulement pompe piscine",
        ],
    },
    "electromenager_joint": {
        "niche": "electromenager",
        "sub_niche": "joint_hublot",
        "keywords": [
            "joint hublot lave linge",
            "manchette lave linge",
            "joint porte lave vaisselle",
            "joint four encastrable",
            "joint cocotte minute",
            "joint autocuiseur seb",
            "joint porte refrigerateur",
            "joint congelateur",
            "soufflet lave linge bosch",
            "joint tambour seche linge",
            "joint cuve lave linge",
            "caoutchouc hublot lave linge",
            "joint etancheite lave vaisselle",
            "bavette porte lave vaisselle",
            "joint resistance lave linge",
        ],
    },
    "electromenager_pompe": {
        "niche": "electromenager",
        "sub_niche": "pompe_moteur",
        "keywords": [
            "pompe vidange lave linge",
            "pompe cyclage lave vaisselle",
            "charbon moteur lave linge",
            "condensateur seche linge",
            "moteur hotte aspirante",
            "pompe de relevage climatiseur",
            "electrovanne lave linge",
            "pressostat lave linge",
            "thermostat seche linge",
            "resistance lave vaisselle",
            "securite porte lave linge",
            "antiparasite lave linge",
            "pompe vidange seche linge",
            "moteur ventilateur four",
            "turbine lave vaisselle",
        ],
    },
    "atelier_ponceuse": {
        "niche": "atelier",
        "sub_niche": "ponceuse",
        "keywords": [
            "plateau ponceuse excentrique",
            "semelle ponceuse bosch",
            "disque abrasif auto agrippant 125",
            "patin ponceuse vibrante",
            "plateau velcro ponceuse",
            "disque abrasif 150mm",
            "feuille abrasive ponceuse",
            "plateau support ponceuse",
            "mousse interface ponceuse",
            "bague adaptation ponceuse",
            "brosse ponceuse",
            "sac aspirateur ponceuse",
            "plateau ponceuse makita",
            "plateau ponceuse dewalt",
            "plateau ponceuse festool",
        ],
    },
    "atelier_adaptateur": {
        "niche": "atelier",
        "sub_niche": "adaptateur",
        "keywords": [
            "mandrin perceuse autoserrant",
            "adaptateur sds plus",
            "douille reduction perceuse",
            "foret etage",
            "porte embout magnetique",
            "rallonge flexible visseuse",
            "renvoi angle perceuse",
            "mandrin adaptation",
            "cle mandrin perceuse",
            "adaptateur douille impact",
            "douille cardan",
            "rallonge porte embout",
            "adaptateur six pans",
            "bague reduction scie",
            "guide percage",
        ],
    },
    "aspirateur_filtre": {
        "niche": "aspirateur",
        "sub_niche": "filtre",
        "keywords": [
            "filtre robot aspirateur",
            "filtre hepa aspirateur traineau",
            "filtre aspirateur cyclonique",
            "filtre aspirateur karcher",
            "filtre aspirateur dyson",
            "filtre mousse aspirateur",
            "pre filtre aspirateur",
            "filtre moteur aspirateur",
            "filtre aspirateur eau et poussiere",
            "filtre aspirateur rowenta",
            "filtre aspirateur bosch",
            "filtre cartouche aspirateur",
            "filtre sortie air aspirateur",
            "sac aspirateur universel",
            "filtre aspirateur sans sac",
        ],
    },
    "aspirateur_brosse": {
        "niche": "aspirateur",
        "sub_niche": "brosse",
        "keywords": [
            "brosse laterale robot aspirateur",
            "brosse principale robot aspirateur",
            "rouleau brosse aspirateur",
            "turbo brosse aspirateur traineau",
            "brosse parquet aspirateur",
            "suceur long aspirateur",
            "brosse meuble aspirateur",
            "embout brosse aspirateur",
            "electro brosse aspirateur",
            "brosse aspirateur poil animaux",
            "brosse sol dur aspirateur",
            "mini turbo brosse",
            "flexible aspirateur universel",
            "tube aspirateur telescopique",
            "tuyau aspirateur",
        ],
    },
}


def _update_campaign_status(
    db: Session,
    campaign_id: uuid.UUID,
    status: str,
    phase: str = "",
    progress_pct: int = 0,
    error_message: str = "",
) -> None:
    """Update campaign status in DB."""
    campaign = db.query(SearchCampaign).filter(SearchCampaign.id == campaign_id).first()
    if campaign:
        campaign.status = status
        campaign.phase = phase
        campaign.progress_pct = progress_pct
        if error_message:
            campaign.error_message = error_message
        if status == "completed":
            campaign.completed_at = datetime.now(timezone.utc)
        db.commit()


PRODUCT_UPDATE_KEYS = (
    "title", "brand", "category", "marketplace", "price", "currency", "bsr",
    "monthly_sales", "review_count", "rating", "seller_count", "image_url",
    "source", "amazon_is_seller", "buybox_seller", "buybox_price", "price_stability",
)


def _upsert_product(db: Session, data: dict[str, Any], user_id: str, niche: str, sub_niche: str) -> Product:
    """Upsert product by ASIN."""
    asin = data.get("asin", "")
    existing = db.query(Product).filter(Product.asin == asin).first()
    product_data = {k: v for k, v in data.items() if k in PRODUCT_UPDATE_KEYS and v is not None}
    product_data["asin"] = asin
    product_data["niche"] = niche
    product_data["sub_niche"] = sub_niche
    product_data["user_id"] = uuid.UUID(user_id) if user_id else None
    product_data.setdefault("marketplace", data.get("marketplace") or "amazon_fr")
    product_data.setdefault("currency", "EUR")

    if existing:
        for k, v in product_data.items():
            if v is not None and k != "id":
                setattr(existing, k, v)
        if "raw_data" in data:
            existing.raw_data = data["raw_data"]
        return existing
    else:
        product = Product(**product_data, raw_data=data.get("raw_data"))
        db.add(product)
        db.flush()
        return product


async def run_campaign(campaign_id: str, user_id: str) -> None:
    """
    Run a search campaign through 4 phases:
    - Phase 1 (amazon_search): Search Amazon by keyword, collect ASINs
    - Phase 2 (keepa): Enrich ASINs in batches of 100
    - Phase 3 (spapi): Get competitive pricing (optional if no SP-API credentials)
    - Phase 4 (scoring): Score products, save opportunities
    """
    db = SessionLocal()
    campaign_uuid = uuid.UUID(campaign_id)

    try:
        campaign = db.query(SearchCampaign).filter(SearchCampaign.id == campaign_uuid).first()
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return

        _update_campaign_status(db, campaign_uuid, "running", "amazon_search", 0)

        keywords = campaign.keywords or []
        filters = campaign.filters or {}
        marketplace = campaign.marketplace
        niche = campaign.niche or ""
        sub_niche = campaign.sub_niche or ""

        # Phase 1: Amazon Search - collect ASINs per keyword
        asin_to_keyword: dict[str, str] = {}
        asin_to_rank: dict[str, int] = {}
        rank_counter = 0

        from app.services.amazon_search_service import AmazonSearchService

        searcher = AmazonSearchService()
        try:
            for i, keyword in enumerate(keywords):
                pct = int(5 + (i / max(len(keywords), 1)) * 20)
                _update_campaign_status(db, campaign_uuid, "running", "amazon_search", pct)

                products = await searcher.search_by_keyword(
                    keyword=keyword, filters=filters, marketplace=marketplace
                )
                for p in products:
                    asin = p.get("asin")
                    if asin and asin not in asin_to_keyword:
                        asin_to_keyword[asin] = keyword
                        rank_counter += 1
                        asin_to_rank[asin] = rank_counter

                await asyncio.sleep(random.uniform(3, 7))
            await searcher.close()
        except Exception as e:
            logger.exception(f"Amazon search phase error: {e}")
            _update_campaign_status(db, campaign_uuid, "error", "amazon_search", 0, str(e))
            return

        asins = list(asin_to_keyword.keys())
        if not asins:
            logger.warning(f"Campaign {campaign_id}: no ASINs found in phase 1")
            _update_campaign_status(db, campaign_uuid, "completed", "amazon_search", 25)
            campaign.found_count = 0
            db.commit()
            return

        # Phase 2: Keepa - enrich in batches of 100
        _update_campaign_status(db, campaign_uuid, "running", "keepa", 30)

        from app.services.keepa_client import KeepaClient

        keepa = KeepaClient()
        enriched_products = await keepa.enrich_batch(asins, marketplace=marketplace)

        enriched_by_asin = {p["asin"]: p for p in enriched_products}
        _update_campaign_status(db, campaign_uuid, "running", "keepa", 50)

        # Phase 3: SP-API (optional, errors don't stop the pipeline)
        settings = get_settings()
        spapi_configured = bool(
            settings.SPAPI_LWA_CLIENT_ID
            and settings.SPAPI_LWA_CLIENT_SECRET
            and settings.SPAPI_LWA_REFRESH_TOKEN
        )

        if spapi_configured:
            try:
                from app.services.spapi_client import SPAPIClient

                spapi = SPAPIClient()
                for i, asin in enumerate(asins[:50]):
                    pct = 50 + int((i / max(len(asins[:50]), 1)) * 20)
                    _update_campaign_status(db, campaign_uuid, "running", "spapi", pct)
                    try:
                        pricing = await spapi.get_competitive_pricing(asin)
                        if pricing and asin in enriched_by_asin:
                            from app.services.spapi_enrichment_service import _parse_competitive_pricing
                            spapi_data = _parse_competitive_pricing(pricing)
                            if spapi_data:
                                enriched_by_asin[asin].setdefault("raw_data", {})
                                enriched_by_asin[asin]["raw_data"]["spapi"] = spapi_data
                                if "buybox_price" in spapi_data:
                                    enriched_by_asin[asin]["buybox_price"] = spapi_data["buybox_price"]
                    except Exception:
                        logger.debug(f"SP-API error for {asin}, skipping")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"SP-API phase skipped due to error: {e}")
        else:
            logger.info("SP-API not configured, skipping phase 3")

        # Phase 4: Scoring - upsert products, create SearchResults, score, save opportunities
        _update_campaign_status(db, campaign_uuid, "running", "scoring", 75)

        from app.services.scoring_service import score_product

        product_objs: list[Product] = []
        for i, asin in enumerate(asins):
            data = enriched_by_asin.get(asin)
            if not data:
                data = {"asin": asin, "marketplace": marketplace, "source": "amazon_search"}
            else:
                data.setdefault("marketplace", marketplace)

            product = _upsert_product(db, data, user_id, niche, sub_niche)
            product_objs.append(product)

            # Create SearchResult
            sr = SearchResult(
                campaign_id=campaign_uuid,
                product_id=product.id,
                keyword=asin_to_keyword.get(asin, ""),
                rank_at_discovery=asin_to_rank.get(asin),
                source="helium10",
            )
            db.add(sr)

        db.commit()

        # Refresh products for scoring (need to reload after commit)
        for product in product_objs:
            db.refresh(product)

        # Score and save opportunities
        for i, product in enumerate(product_objs):
            pct = 75 + int((i / max(len(product_objs), 1)) * 24)
            _update_campaign_status(db, campaign_uuid, "running", "scoring", pct)

            score_result = score_product(product, cost_price=None)
            opp = Opportunity(
                product_id=product.id,
                campaign_id=campaign_uuid,
                user_id=uuid.UUID(user_id) if user_id else None,
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

        campaign.found_count = len(product_objs)
        _update_campaign_status(db, campaign_uuid, "completed", "scoring", 100)
        logger.info(f"Campaign {campaign_id} completed: {len(product_objs)} products, {len(product_objs)} opportunities")

    except Exception as e:
        logger.exception(f"Campaign {campaign_id} error: {e}")
        _update_campaign_status(db, campaign_uuid, "error", "", 0, str(e))
    finally:
        db.close()
