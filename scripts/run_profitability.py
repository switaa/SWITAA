"""Run profitability recalculation on the server."""
import sys
import os

sys.path.insert(0, "/app")
os.chdir("/app")

from app.core.database import SessionLocal
from app.services.profitability_service import enrich_opportunities_with_profitability


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "fbm"
    margin = float(sys.argv[2]) if len(sys.argv) > 2 else 35.0
    db = SessionLocal()
    try:
        print(f"Recalculating profitability (mode={mode}, margin={margin}%)...")
        result = enrich_opportunities_with_profitability(db, target_margin_pct=margin, mode=mode)
        print(f"Result: {result}")
    finally:
        db.close()


main()
