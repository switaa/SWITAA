import sys
sys.path.insert(0, "/app")
from app.core.database import SessionLocal
from app.models.product import Product
from app.models.opportunity import Opportunity
from sqlalchemy import func

db = SessionLocal()

total_opp = db.query(Opportunity).count()
with_score = db.query(Opportunity).filter(Opportunity.score >= 40).count()
with_price = db.query(Product).filter(Product.price > 0).count()

joined = (
    db.query(func.count())
    .select_from(Product)
    .join(Opportunity, Opportunity.product_id == Product.id)
).scalar()

filtered = (
    db.query(func.count())
    .select_from(Product)
    .join(Opportunity, Opportunity.product_id == Product.id)
    .filter(Opportunity.score >= 40)
    .filter(Product.price > 0)
).scalar()

print(f"Total opportunities: {total_opp}")
print(f"Score >= 40: {with_score}")
print(f"Products price > 0: {with_price}")
print(f"Joined products+opportunities: {joined}")
print(f"After score+price filter: {filtered}")

sample = (
    db.query(Opportunity.score, Product.price, Product.bsr, Product.amazon_is_seller)
    .join(Product, Opportunity.product_id == Product.id)
    .order_by(Opportunity.score.desc())
    .limit(5)
    .all()
)
print(f"\nTop 5 by score:")
for s in sample:
    print(f"  score={s[0]:.1f} price={s[1]} bsr={s[2]} amazon={s[3]}")

db.close()
