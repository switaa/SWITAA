"""Import supplier catalogs via FTP/SFTP."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

import paramiko

from app.core.database import SessionLocal
from app.models.supplier import Supplier, SupplierProduct

logger = logging.getLogger("marcus.supplier_feed")


async def import_supplier_catalog(supplier_id: str):
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            logger.error(f"Supplier {supplier_id} not found")
            return

        logger.info(f"Importing catalog from {supplier.name} ({supplier.access_type})")

        if supplier.access_type.upper() == "SFTP":
            content = _download_sftp(supplier)
        else:
            content = _download_ftp(supplier)

        if not content:
            logger.error(f"No data downloaded from {supplier.name}")
            return

        rows = _parse_csv(content, supplier)
        logger.info(f"Parsed {len(rows)} rows from {supplier.name}")

        saved = 0
        for row in rows:
            existing = (
                db.query(SupplierProduct)
                .filter(
                    SupplierProduct.supplier_id == supplier.id,
                    SupplierProduct.sku == row["sku"],
                )
                .first()
            )
            if existing:
                existing.price_ht = row["price_ht"]
                existing.stock = row.get("stock", 0)
                existing.ean = row.get("ean")
                existing.asin = row.get("asin")
                existing.title = row.get("title", "")
            else:
                sp = SupplierProduct(supplier_id=supplier.id, **row)
                db.add(sp)
            saved += 1

        db.commit()
        logger.info(f"Imported {saved} products from {supplier.name}")

    except Exception as e:
        logger.error(f"Import error for {supplier_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _download_sftp(supplier: Supplier) -> str:
    transport = paramiko.Transport((supplier.host, supplier.port or 22))
    transport.connect(username=supplier.username, password=supplier.password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    remote_path = supplier.csv_path or supplier.root_path
    buf = io.BytesIO()
    sftp.getfo(remote_path, buf)
    sftp.close()
    transport.close()

    return buf.getvalue().decode(supplier.encoding or "utf-8")


def _download_ftp(supplier: Supplier) -> str:
    import ftplib

    ftp = ftplib.FTP()
    ftp.connect(supplier.host, supplier.port or 21)
    ftp.login(supplier.username, supplier.password)

    remote_path = supplier.csv_path or supplier.root_path
    buf = io.BytesIO()
    ftp.retrbinary(f"RETR {remote_path}", buf.write)
    ftp.quit()

    return buf.getvalue().decode(supplier.encoding or "utf-8")


def _parse_csv(content: str, supplier: Supplier) -> list[dict[str, Any]]:
    mapping = supplier.mapping_json or {}
    delimiter = supplier.delimiter or ";"
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    rows = []
    for raw_row in reader:
        sku_col = mapping.get("sku", "sku")
        price_col = mapping.get("price_ht", "price_ht")
        ean_col = mapping.get("ean", "ean")
        asin_col = mapping.get("asin", "asin")
        title_col = mapping.get("title", "title")
        stock_col = mapping.get("stock", "stock")

        sku = raw_row.get(sku_col, "").strip()
        if not sku:
            continue

        price_str = raw_row.get(price_col, "0").replace(",", ".").strip()
        try:
            price = float(price_str)
        except ValueError:
            price = 0.0

        stock_str = raw_row.get(stock_col, "0").strip()
        try:
            stock = int(stock_str)
        except ValueError:
            stock = 0

        rows.append({
            "sku": sku,
            "price_ht": price,
            "ean": raw_row.get(ean_col, "").strip() or None,
            "asin": raw_row.get(asin_col, "").strip() or None,
            "title": raw_row.get(title_col, "").strip(),
            "stock": stock,
        })

    return rows
