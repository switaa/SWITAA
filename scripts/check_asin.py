"""Check a specific ASIN in the Marcus database."""
import sys
sys.path.insert(0, "/app")
from app.core.database import SessionLocal
from app.models.product import Product
from app.models.opportunity import Opportunity

asin = sys.argv[1] if len(sys.argv) > 1 else "B0DFHXNG82"
db = SessionLocal()
p = db.query(Product).filter(Product.asin == asin).first()
if p:
    print(f"ASIN: {p.asin}")
    print(f"Titre: {p.title}")
    print(f"Prix: {p.price} EUR")
    print(f"BSR: {p.bsr_rank}")
    print(f"Reviews: {p.review_count}")
    print(f"Rating: {p.rating}")
    print(f"Amazon vendeur: {p.amazon_is_seller}")
    print(f"BuyBox: {p.buybox_price}")
    print(f"Categorie: {p.category}")
    print(f"Niche: {p.sub_niche}")
    opp = db.query(Opportunity).filter(Opportunity.product_id == p.id).first()
    if opp:
        print(f"Score: {opp.score}")
        print(f"Raison: {opp.reason}")
    else:
        print("Pas d'opportunite associee")
else:
    print(f"ASIN {asin} NON TROUVE dans la base Marcus")
db.close()
