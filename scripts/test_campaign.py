"""Test a single campaign to debug the pipeline."""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format="%(asctime)s %(name)s %(levelname)s %(message)s")

async def main():
    from app.services.helium10_service import Helium10Service

    h10 = Helium10Service()
    print(f"H10 email: {h10.email}")
    print(f"H10 password set: {bool(h10.password)}")

    print("\n--- Testing login ---")
    ok = await h10.login()
    print(f"Login result: {ok}")

    if ok:
        print("\n--- Testing search ---")
        results = await h10.search_by_keyword(
            keyword="vanne 6 voies piscine",
            filters={"marketplace": "amazon_fr"}
        )
        print(f"Found {len(results)} products")
        for r in results[:5]:
            print(f"  {r['asin']} - {r['title'][:60]} - {r['price']} EUR")

    await h10.close()

asyncio.run(main())
