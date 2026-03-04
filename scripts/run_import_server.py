import sys
sys.path.insert(0, "/app")
from app.core.database import SessionLocal
from app.services.csv_import_service import import_all_csvs

db = SessionLocal()
try:
    results = import_all_csvs(db, "/app/CSV")
    for r in results:
        niche = r["niche"]
        imported = r["imported"]
        opps = r.get("opportunities_created", 0)
        skipped = r["skipped"]
        errors = r["errors"]
        print(niche, "|", imported, "imported |", opps, "opps |", skipped, "skip |", errors, "err")
    total_p = sum(r["imported"] for r in results)
    total_o = sum(r.get("opportunities_created", 0) for r in results)
    print("---")
    print("TOTAL:", total_p, "products,", total_o, "opportunities")
finally:
    db.close()
