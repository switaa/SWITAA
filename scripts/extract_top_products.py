"""Extract top products with profitability data from the database."""
import sys
import os
import csv

sys.path.insert(0, "/app")
os.chdir("/app")

from sqlalchemy import desc
from app.core.database import SessionLocal
from app.models.product import Product
from app.models.opportunity import Opportunity


def main():
    db = SessionLocal()
    try:
        rows = (
            db.query(
                Product.asin,
                Product.title,
                Product.brand,
                Product.niche,
                Product.price,
                Product.buybox_price,
                Product.bsr,
                Product.monthly_sales,
                Product.seller_count,
                Product.review_count,
                Product.rating,
                Product.amazon_is_seller,
                Product.price_stability,
                Opportunity.score,
                Opportunity.cost_price,
                Opportunity.marketplace_fees,
                Opportunity.margin_pct,
                Opportunity.decision,
            )
            .join(Opportunity, Opportunity.product_id == Product.id)
            .filter(Opportunity.score >= 30)
            .filter(Product.price > 10)
            .order_by(desc(Opportunity.score))
            .limit(100)
            .all()
        )

        print(f"\n{'='*100}")
        print(f"TOP {len(rows)} PRODUITS - Tri par score (marge cible 35% FBM)")
        print(f"{'='*100}\n")

        for i, r in enumerate(rows[:30], 1):
            amz = "AMZ" if r.amazon_is_seller else "3P" if r.amazon_is_seller is False else "?"
            stability = r.price_stability or "?"
            buybox = f"{float(r.buybox_price):.0f}E" if r.buybox_price else "-"
            max_cost = float(r.cost_price) if r.cost_price else 0
            fees = float(r.marketplace_fees) if r.marketplace_fees else 0

            print(f"{i:2d}. [{r.asin}] Score:{float(r.score):5.1f} | "
                  f"Prix:{float(r.price):6.0f}E BuyBox:{buybox:>5s} | "
                  f"BSR:{r.bsr or 0:>7d} Ventes:{r.monthly_sales or 0:>4d}/m | "
                  f"Vendeurs:{r.seller_count or 0:>2d} {amz} | "
                  f"Cout max:{max_cost:6.1f}E Frais:{fees:5.1f}E | "
                  f"Stab:{stability:>8s} | {r.niche or '?'}")
            print(f"    {r.title[:90]}")
            print()

        print(f"\n{'='*60}")
        print("STATS GLOBALES")
        print(f"{'='*60}")

        niches = {}
        total_potential = 0
        for r in rows:
            n = r.niche or "autre"
            niches[n] = niches.get(n, 0) + 1
            total_potential += (r.monthly_sales or 0) * float(r.price)

        print(f"Produits avec score >= 30 : {len(rows)}")
        print(f"CA potentiel total/mois : {total_potential:,.0f} EUR")
        print(f"\nRepartition par niche :")
        for n, c in sorted(niches.items(), key=lambda x: -x[1]):
            print(f"  {n}: {c} produits")

        a_count = sum(1 for r in rows if r.decision == "A_launch")
        b_count = sum(1 for r in rows if r.decision == "B_review")
        print(f"\nDecisions : A(lancer)={a_count} B(revoir)={b_count}")

        no_amz = sum(1 for r in rows if r.amazon_is_seller is False)
        print(f"Sans Amazon vendeur : {no_amz}/{len(rows)}")

    finally:
        db.close()


main()
