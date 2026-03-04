"""Check SP-API enrichment statistics."""
import sys
sys.path.insert(0, "/app")

from app.core.database import SessionLocal
from app.models.product import Product
from sqlalchemy import text

db = SessionLocal()
total = db.query(Product).count()

enriched = db.execute(text(
    "SELECT COUNT(*) FROM products WHERE raw_data::jsonb ? 'spapi'"
)).scalar()

with_buybox = db.execute(text(
    "SELECT COUNT(*) FROM products WHERE buybox_price IS NOT NULL AND buybox_price > 0"
)).scalar()

print(f"Total produits:          {total}")
print(f"Enrichis SP-API:         {enriched}")
print(f"Avec prix BuyBox:        {with_buybox}")
print(f"Sans donnees SP-API:     {total - enriched}")

print("\n--- Top 10 produits par prix BuyBox ---")
rows = db.execute(text("""
    SELECT asin, title, buybox_price, bsr_rank
    FROM products
    WHERE buybox_price IS NOT NULL AND buybox_price > 0
    ORDER BY buybox_price DESC
    LIMIT 10
""")).fetchall()
for r in rows:
    title = (r[1] or "")[:50]
    print(f"  {r[0]}  {r[2]:>8.2f}EUR  BSR:{r[3] or 'N/A':<8}  {title}")

db.close()
