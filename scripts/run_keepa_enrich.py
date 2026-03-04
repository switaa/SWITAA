import sys
import asyncio
sys.path.insert(0, "/app")
from app.core.database import SessionLocal
from app.services.enrichment_service import run_keepa_enrichment

async def main():
    db = SessionLocal()
    try:
        result = await run_keepa_enrichment(db, source_filter="helium10_blackbox", marketplace="amazon_fr")
        for k, v in result.items():
            print(k, ":", v)
    finally:
        db.close()

asyncio.run(main())
