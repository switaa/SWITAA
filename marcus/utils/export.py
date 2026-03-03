from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from marcus.core.models import Database

logger = logging.getLogger("marcus.export")

EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "exports"


def export_opportunities_csv(db: Database, min_score: float = 0, output_path: Path | None = None) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EXPORT_DIR / f"opportunities_{ts}.csv"

    rows = db.get_opportunities(min_score=min_score, limit=500)
    if not rows:
        logger.warning("No opportunities to export")
        return output_path

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Exported {len(rows)} opportunities to {output_path}")
    return output_path


def export_opportunities_excel(db: Database, min_score: float = 0, output_path: Path | None = None) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EXPORT_DIR / f"opportunities_{ts}.xlsx"

    rows = db.get_opportunities(min_score=min_score, limit=500)
    if not rows:
        logger.warning("No opportunities to export")
        return output_path

    df = pd.DataFrame(rows)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Opportunites")

        products = db.get_products(limit=500)
        if products:
            pd.DataFrame(products).to_excel(writer, index=False, sheet_name="Produits")

    logger.info(f"Exported {len(rows)} opportunities to {output_path}")
    return output_path


def export_products_csv(db: Database, marketplace: str | None = None, output_path: Path | None = None) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{marketplace}" if marketplace else ""
        output_path = EXPORT_DIR / f"products{suffix}_{ts}.csv"

    rows = db.get_products(marketplace=marketplace, limit=1000)
    if not rows:
        logger.warning("No products to export")
        return output_path

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Exported {len(rows)} products to {output_path}")
    return output_path
