"""
Standalone script to import Helium 10 Black Box CSV exports into Marcus DB.

Usage:
    # From inside the backend Docker container:
    python scripts/import_h10_csvs.py /app/data/csv

    # Or via API after deployment:
    python scripts/import_h10_csvs.py --api https://marcus.w3lg.fr --email user@example.com
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

NICHE_MAP = {
    "1": {"niche": "piscine", "sub_niche": "filtration"},
    "2": {"niche": "chauffage", "sub_niche": "pieces_detachees"},
    "3": {"niche": "electromenager", "sub_niche": "aspirateur"},
    "4": {"niche": "automobile", "sub_niche": "pieces_detachees"},
    "5": {"niche": "plomberie", "sub_niche": "robinet"},
    "6": {"niche": "jardinage", "sub_niche": "tuyau"},
    "7": {"niche": "electricite", "sub_niche": "interrupteur"},
    "8": {"niche": "outillage", "sub_niche": "foret"},
}


def safe_int(val: str) -> int | None:
    if not val or val in ("N/A", "", "-"):
        return None
    try:
        return int(float(val.replace(",", "")))
    except (ValueError, TypeError):
        return None


def safe_float(val: str) -> float | None:
    if not val or val in ("N/A", "", "-"):
        return None
    try:
        return float(val.replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_csv(csv_path: Path) -> list[dict[str, Any]]:
    products = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = row.get("ASIN", "").strip()
            if not asin or len(asin) != 10:
                continue

            products.append({
                "asin": asin,
                "title": row.get("Title", "").strip()[:500],
                "brand": row.get("Brand", "").strip()[:255],
                "category": row.get("Category", "").strip()[:255],
                "price": safe_float(row.get("Price", "")),
                "bsr": safe_int(row.get("BSR", "")),
                "monthly_sales": safe_int(row.get("ASIN Sales", "")),
                "review_count": safe_int(row.get("Review Count", "")),
                "rating": safe_float(row.get("Reviews Rating", "")),
                "seller_count": safe_int(row.get("Number of Active Sellers", "")),
                "image_url": row.get("Image URL", "").strip(),
                "fulfillment": row.get("Fulfillment", ""),
                "asin_revenue": safe_float(row.get("ASIN Revenue", "")),
                "subcategory": row.get("Subcategory", ""),
                "seller": row.get("Seller", ""),
                "seller_country": row.get("Seller Country/Region", ""),
                "price_trend_90d": safe_float(row.get("Price Trend (90 days) (%)", "")),
                "sales_trend_90d": safe_float(row.get("Sales Trend (90 days) (%)", "")),
                "weight": safe_float(row.get("Weight", "")),
                "age_months": safe_int(row.get("Age (Month)", "")),
                "variation_count": safe_int(row.get("Variation Count", "")),
            })
    return products


def import_via_db(csv_dir: Path) -> None:
    """Import directly via SQLAlchemy (run inside Docker container or with DB access)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

    from app.core.database import SessionLocal
    from app.services.csv_import_service import import_all_csvs

    db = SessionLocal()
    try:
        results = import_all_csvs(db=db, csv_dir=csv_dir)
        print("\n=== IMPORT RESULTS ===")
        total_products = 0
        total_opps = 0
        for r in results:
            print(f"  {r['niche']:20s} | {r['imported']:4d} products | {r.get('opportunities_created', 0):4d} opportunities | {r['skipped']} skipped | {r['errors']} errors")
            total_products += r["imported"]
            total_opps += r.get("opportunities_created", 0)
        print(f"\n  TOTAL: {total_products} products, {total_opps} opportunities")
    finally:
        db.close()


def import_via_api(csv_dir: Path, api_url: str, email: str, password: str) -> None:
    """Import via HTTP API calls."""
    import httpx

    client = httpx.Client(base_url=api_url, timeout=120)

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for file_num in sorted(NICHE_MAP.keys()):
        niche_info = NICHE_MAP[file_num]
        pattern = f"FR_AMAZON_blackBoxProducts_{file_num}_*.csv"
        matches = list(csv_dir.glob(pattern))

        if not matches:
            print(f"  [SKIP] No CSV for niche {file_num} ({niche_info['niche']})")
            continue

        csv_file = matches[0]
        print(f"  [UPLOAD] {csv_file.name} -> {niche_info['niche']}/{niche_info['sub_niche']}")

        with open(csv_file, "rb") as f:
            resp = client.post(
                "/api/v1/products/import-csv/file",
                params={"niche": niche_info["niche"], "sub_niche": niche_info["sub_niche"]},
                files={"file": (csv_file.name, f, "text/csv")},
                headers=headers,
            )

        if resp.status_code == 200:
            result = resp.json()
            print(f"    -> {result['imported']} imported, {result.get('opportunities_created', 0)} opportunities")
        else:
            print(f"    -> ERROR {resp.status_code}: {resp.text}")

    client.close()


def summary_only(csv_dir: Path) -> None:
    """Parse CSVs locally and display a summary (no DB needed)."""
    print("\n=== HELIUM 10 CSV SUMMARY ===\n")
    grand_total = 0

    for file_num in sorted(NICHE_MAP.keys()):
        niche_info = NICHE_MAP[file_num]
        pattern = f"FR_AMAZON_blackBoxProducts_{file_num}_*.csv"
        matches = list(csv_dir.glob(pattern))

        if not matches:
            print(f"  Niche {file_num} ({niche_info['niche']:15s}): FILE NOT FOUND")
            continue

        products = parse_csv(matches[0])
        grand_total += len(products)

        prices = [p["price"] for p in products if p["price"]]
        sellers = [p["seller_count"] for p in products if p["seller_count"]]
        sales = [p["monthly_sales"] for p in products if p["monthly_sales"]]

        avg_price = sum(prices) / len(prices) if prices else 0
        avg_sellers = sum(sellers) / len(sellers) if sellers else 0
        avg_sales = sum(sales) / len(sales) if sales else 0

        print(f"  Niche {file_num} ({niche_info['niche']:15s}): {len(products):4d} products | "
              f"avg price: {avg_price:7.2f}EUR | avg sellers: {avg_sellers:4.1f} | avg sales: {avg_sales:6.0f}/mo")

    print(f"\n  GRAND TOTAL: {grand_total} product references")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Helium 10 CSVs into Marcus")
    parser.add_argument("csv_dir", nargs="?", default="C:/DEV/SWITAA/CSV", help="Directory with CSV files")
    parser.add_argument("--api", help="API base URL (e.g. https://marcus.w3lg.fr)")
    parser.add_argument("--email", help="API login email")
    parser.add_argument("--password", help="API login password")
    parser.add_argument("--summary", action="store_true", help="Only show CSV summary, no import")
    parser.add_argument("--db", action="store_true", help="Import via direct DB access (inside Docker)")

    args = parser.parse_args()
    csv_dir = Path(args.csv_dir)

    if not csv_dir.exists():
        print(f"ERROR: Directory not found: {csv_dir}")
        sys.exit(1)

    if args.summary:
        summary_only(csv_dir)
    elif args.api:
        if not args.email or not args.password:
            print("ERROR: --email and --password required with --api")
            sys.exit(1)
        import_via_api(csv_dir, args.api, args.email, args.password)
    elif args.db:
        import_via_db(csv_dir)
    else:
        summary_only(csv_dir)
        print("\n  Use --db for direct import or --api for API import")
