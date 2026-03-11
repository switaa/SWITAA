"""Get top 100 ASINs for Tactical Arbitrage reverse search."""
import sys
sys.path.insert(0, "/app")
from app.core.database import SessionLocal
from app.models.product import Product
from app.models.opportunity import Opportunity

db = SessionLocal()
rows = (
    db.query(Product.asin, Product.price, Opportunity.score)
    .join(Opportunity, Opportunity.product_id == Product.id)
    .filter(Opportunity.score >= 30)
    .filter(Product.price > 15)
    .filter(Product.price < 200)
    .filter((Product.amazon_is_seller == False) | (Product.amazon_is_seller.is_(None)))
    .order_by(Opportunity.score.desc())
    .limit(100)
    .all()
)
asins = [r[0] for r in rows]
print("\n".join(asins))
print(f"\n--- Total: {len(asins)} ASINs ---")
db.close()
