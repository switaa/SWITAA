"""Run SP-API enrichment on the server."""
import asyncio
import sys
import os

sys.path.insert(0, "/app")
os.chdir("/app")

from app.core.database import SessionLocal
from app.services.spapi_enrichment_service import run_spapi_enrichment


async def main():
    max_products = int(sys.argv[1]) if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        print(f"Starting SP-API enrichment (max={max_products})...")
        result = await run_spapi_enrichment(
            db=db,
            source_filter="helium10_blackbox",
            force=False,
            max_products=max_products,
            delay_between=0.6,
        )
        print(f"Result: {result}")
    finally:
        db.close()


asyncio.run(main())
