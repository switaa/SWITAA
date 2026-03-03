from __future__ import annotations

import logging
from typing import Optional

from marcus.config.settings import SCORING_THRESHOLDS, SCORING_WEIGHTS
from marcus.core.models import Database, Opportunity, Product

logger = logging.getLogger("marcus.analyzer")


class ProductAnalyzer:
    def __init__(self, db: Database):
        self.db = db
        self.weights = SCORING_WEIGHTS
        self.thresholds = SCORING_THRESHOLDS

    def analyze(self, product: Product, cost_price: Optional[float] = None) -> Opportunity:
        margin_score = self._score_margin(product, cost_price)
        competition_score = self._score_competition(product)
        demand_score = self._score_demand(product)
        bsr_score = self._score_bsr(product)

        total = (
            margin_score * self.weights["margin"]
            + competition_score * self.weights["competition"]
            + demand_score * self.weights["demand"]
            + bsr_score * self.weights["bsr"]
        )

        estimated_margin = 0.0
        if cost_price and product.price > 0:
            fees = product.price * (product.referral_fee_pct or 15) / 100
            fba = product.fba_fees or 0
            net = product.price - fees - fba - cost_price
            estimated_margin = (net / product.price) * 100

        return Opportunity(
            product=product,
            score=round(total, 2),
            margin_score=round(margin_score, 2),
            competition_score=round(competition_score, 2),
            demand_score=round(demand_score, 2),
            bsr_score=round(bsr_score, 2),
            estimated_margin_pct=round(estimated_margin, 1),
        )

    def analyze_batch(
        self,
        products: list[Product],
        cost_price: Optional[float] = None,
        min_score: float = 0,
    ) -> list[Opportunity]:
        opportunities = []
        for p in products:
            opp = self.analyze(p, cost_price)
            if opp.score >= min_score:
                opportunities.append(opp)
        opportunities.sort(key=lambda o: o.score, reverse=True)
        logger.info(f"Analyzed {len(products)} products, {len(opportunities)} above threshold {min_score}")
        return opportunities

    def save_opportunities(self, opportunities: list[Opportunity]):
        for opp in opportunities:
            self.db.upsert_product(opp.product)
            self.db.save_opportunity(opp)
        logger.info(f"Saved {len(opportunities)} opportunities to database")

    def _score_margin(self, product: Product, cost_price: Optional[float]) -> float:
        if not cost_price or product.price <= 0:
            return 50.0

        fees = product.price * (product.referral_fee_pct or 15) / 100
        fba = product.fba_fees or 0
        net = product.price - fees - fba - cost_price
        margin_pct = (net / product.price) * 100

        min_margin = self.thresholds["min_margin_pct"]
        if margin_pct >= min_margin * 2:
            return 100.0
        if margin_pct >= min_margin:
            return 50 + (margin_pct - min_margin) / min_margin * 50
        if margin_pct > 0:
            return margin_pct / min_margin * 50
        return 0.0

    def _score_competition(self, product: Product) -> float:
        sellers = product.seller_count
        reviews = product.review_count
        max_sellers = self.thresholds["max_competition_sellers"]

        score = 50.0

        if sellers is not None:
            if sellers <= 5:
                score = 100.0
            elif sellers <= max_sellers:
                score = 100 - (sellers / max_sellers) * 60
            else:
                score = max(0, 40 - (sellers - max_sellers) / 10)

        if reviews is not None:
            if reviews < 50:
                score = min(100, score + 20)
            elif reviews < 200:
                score = min(100, score + 10)
            elif reviews > 1000:
                score = max(0, score - 15)

        return min(100, max(0, score))

    def _score_demand(self, product: Product) -> float:
        sales = product.monthly_sales
        min_sales = self.thresholds["min_monthly_sales"]

        if sales is None:
            return 50.0

        if sales >= min_sales * 10:
            return 100.0
        if sales >= min_sales:
            return 50 + (sales - min_sales) / (min_sales * 9) * 50
        if sales > 0:
            return sales / min_sales * 50
        return 0.0

    def _score_bsr(self, product: Product) -> float:
        bsr = product.bsr
        max_bsr = self.thresholds["max_bsr"]

        if bsr is None:
            return 50.0

        if bsr <= 1000:
            return 100.0
        if bsr <= max_bsr:
            ratio = bsr / max_bsr
            return 100 - ratio * 60
        return max(0, 40 - (bsr - max_bsr) / max_bsr * 40)
