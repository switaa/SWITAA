import sys
import asyncio
sys.path.insert(0, "/app")
from app.core.database import SessionLocal
from app.services.enrichment_service import run_keepa_enrichment

async def main():
    db = SessionLocal()
    try:
        max_products = int(sys.argv[1]) if len(sys.argv) > 1 else None
        result = await run_keepa_enrichment(
            db,
            source_filter="helium10_blackbox",
            marketplace="amazon_fr",
            max_products=max_products,
        )
        for k, v in result.items():
            print(k, ":", v)
    finally:
        db.close()

asyncio.run(main())
