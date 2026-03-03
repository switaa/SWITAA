from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    asin: str
    title: str
    brand: str = ""
    category: str = ""
    price: float = 0.0
    currency: str = "EUR"
    marketplace: str = "amazon_fr"
    bsr: Optional[int] = None
    monthly_sales: Optional[int] = None
    review_count: Optional[int] = None
    rating: Optional[float] = None
    seller_count: Optional[int] = None
    fba_fees: Optional[float] = None
    referral_fee_pct: Optional[float] = None
    weight_kg: Optional[float] = None
    image_url: str = ""
    source: str = ""
    scraped_at: datetime = Field(default_factory=datetime.now)


class PriceHistory(BaseModel):
    asin: str
    marketplace: str
    date: datetime
    price: float
    bsr: Optional[int] = None
    source: str = ""


class Opportunity(BaseModel):
    product: Product
    score: float = 0.0
    margin_score: float = 0.0
    competition_score: float = 0.0
    demand_score: float = 0.0
    bsr_score: float = 0.0
    estimated_margin_pct: float = 0.0
    notes: str = ""
    discovered_at: datetime = Field(default_factory=datetime.now)


class Database:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                asin TEXT,
                marketplace TEXT,
                title TEXT,
                brand TEXT DEFAULT '',
                category TEXT DEFAULT '',
                price REAL DEFAULT 0,
                currency TEXT DEFAULT 'EUR',
                bsr INTEGER,
                monthly_sales INTEGER,
                review_count INTEGER,
                rating REAL,
                seller_count INTEGER,
                fba_fees REAL,
                referral_fee_pct REAL,
                weight_kg REAL,
                image_url TEXT DEFAULT '',
                source TEXT DEFAULT '',
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (asin, marketplace)
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                date TIMESTAMP NOT NULL,
                price REAL NOT NULL,
                bsr INTEGER,
                source TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                score REAL DEFAULT 0,
                margin_score REAL DEFAULT 0,
                competition_score REAL DEFAULT 0,
                demand_score REAL DEFAULT 0,
                bsr_score REAL DEFAULT 0,
                estimated_margin_pct REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asin, marketplace) REFERENCES products(asin, marketplace)
            );

            CREATE INDEX IF NOT EXISTS idx_price_history_asin
                ON price_history(asin, marketplace);
            CREATE INDEX IF NOT EXISTS idx_opportunities_score
                ON opportunities(score DESC);
        """)
        self.conn.commit()

    def upsert_product(self, product: Product):
        self.conn.execute("""
            INSERT INTO products (
                asin, marketplace, title, brand, category, price, currency,
                bsr, monthly_sales, review_count, rating, seller_count,
                fba_fees, referral_fee_pct, weight_kg, image_url, source, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asin, marketplace) DO UPDATE SET
                title=excluded.title, brand=excluded.brand, category=excluded.category,
                price=excluded.price, bsr=excluded.bsr, monthly_sales=excluded.monthly_sales,
                review_count=excluded.review_count, rating=excluded.rating,
                seller_count=excluded.seller_count, fba_fees=excluded.fba_fees,
                referral_fee_pct=excluded.referral_fee_pct, weight_kg=excluded.weight_kg,
                image_url=excluded.image_url, source=excluded.source, scraped_at=excluded.scraped_at
        """, (
            product.asin, product.marketplace, product.title, product.brand,
            product.category, product.price, product.currency, product.bsr,
            product.monthly_sales, product.review_count, product.rating,
            product.seller_count, product.fba_fees, product.referral_fee_pct,
            product.weight_kg, product.image_url, product.source,
            product.scraped_at.isoformat(),
        ))
        self.conn.commit()

    def add_price_history(self, entry: PriceHistory):
        self.conn.execute("""
            INSERT INTO price_history (asin, marketplace, date, price, bsr, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.asin, entry.marketplace, entry.date.isoformat(),
            entry.price, entry.bsr, entry.source,
        ))
        self.conn.commit()

    def save_opportunity(self, opp: Opportunity):
        self.conn.execute("""
            INSERT INTO opportunities (
                asin, marketplace, score, margin_score, competition_score,
                demand_score, bsr_score, estimated_margin_pct, notes, discovered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            opp.product.asin, opp.product.marketplace, opp.score,
            opp.margin_score, opp.competition_score, opp.demand_score,
            opp.bsr_score, opp.estimated_margin_pct, opp.notes,
            opp.discovered_at.isoformat(),
        ))
        self.conn.commit()

    def get_products(self, marketplace: str | None = None, limit: int = 100) -> list[dict]:
        if marketplace:
            rows = self.conn.execute(
                "SELECT * FROM products WHERE marketplace = ? ORDER BY scraped_at DESC LIMIT ?",
                (marketplace, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM products ORDER BY scraped_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_opportunities(self, min_score: float = 0, limit: int = 50) -> list[dict]:
        rows = self.conn.execute("""
            SELECT o.*, p.title, p.brand, p.price, p.category, p.image_url
            FROM opportunities o
            JOIN products p ON o.asin = p.asin AND o.marketplace = p.marketplace
            WHERE o.score >= ?
            ORDER BY o.score DESC
            LIMIT ?
        """, (min_score, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_price_history(self, asin: str, marketplace: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM price_history WHERE asin = ? AND marketplace = ? ORDER BY date",
            (asin, marketplace),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
