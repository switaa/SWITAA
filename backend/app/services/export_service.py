"""Export data to CSV/Excel."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.models.product import Product


def export_opportunities_data(
    db: Session, format: str = "csv", min_score: float = 0
) -> tuple[io.BytesIO, str, str]:
    rows = (
        db.query(
            Product.asin,
            Product.title,
            Product.brand,
            Product.category,
            Product.price,
            Product.marketplace,
            Product.bsr,
            Product.monthly_sales,
            Product.review_count,
            Opportunity.score,
            Opportunity.margin_pct,
            Opportunity.decision,
            Opportunity.cost_price,
        )
        .join(Opportunity, Opportunity.product_id == Product.id)
        .filter(Opportunity.score >= min_score)
        .order_by(Opportunity.score.desc())
        .limit(500)
        .all()
    )

    df = pd.DataFrame(rows, columns=[
        "ASIN", "Title", "Brand", "Category", "Price", "Marketplace",
        "BSR", "Monthly Sales", "Reviews", "Score", "Margin %",
        "Decision", "Cost Price",
    ])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    buf = io.BytesIO()

    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"opportunities_{ts}.xlsx"

    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)
    return buf, "text/csv", f"opportunities_{ts}.csv"
