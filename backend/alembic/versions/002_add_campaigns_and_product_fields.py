"""add search_campaigns, search_results tables and new product fields

Revision ID: 002
Revises: 001
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("niche", sa.String(50), index=True),
        sa.Column("sub_niche", sa.String(100), server_default=""),
        sa.Column("keywords", JSON, server_default="[]"),
        sa.Column("marketplace", sa.String(50), server_default="amazon_fr"),
        sa.Column("status", sa.String(20), server_default="pending", index=True),
        sa.Column("phase", sa.String(50), server_default=""),
        sa.Column("progress_pct", sa.Integer, server_default="0"),
        sa.Column("target_count", sa.Integer, server_default="50"),
        sa.Column("found_count", sa.Integer, server_default="0"),
        sa.Column("filters", JSON, nullable=True),
        sa.Column("error_message", sa.Text, server_default=""),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "search_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("search_campaigns.id", ondelete="CASCADE"), index=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), index=True),
        sa.Column("keyword", sa.String(255), server_default=""),
        sa.Column("rank_at_discovery", sa.Integer, nullable=True),
        sa.Column("source", sa.String(50), server_default=""),
        sa.Column("discovered_at", sa.DateTime),
    )

    op.add_column("products", sa.Column("niche", sa.String(50), nullable=True))
    op.add_column("products", sa.Column("sub_niche", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("amazon_is_seller", sa.Boolean, nullable=True))
    op.add_column("products", sa.Column("buybox_seller", sa.String(255), nullable=True))
    op.add_column("products", sa.Column("buybox_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("price_stability", sa.String(20), nullable=True))
    op.add_column("products", sa.Column("fba_eligible", sa.Boolean, nullable=True))
    op.add_column("products", sa.Column("hazmat", sa.Boolean, nullable=True))
    op.add_column("products", sa.Column("brand_restricted", sa.Boolean, nullable=True))

    op.create_index("ix_products_niche", "products", ["niche"])
    op.create_index("ix_products_sub_niche", "products", ["sub_niche"])


def downgrade() -> None:
    op.drop_index("ix_products_sub_niche", table_name="products")
    op.drop_index("ix_products_niche", table_name="products")

    op.drop_column("products", "brand_restricted")
    op.drop_column("products", "hazmat")
    op.drop_column("products", "fba_eligible")
    op.drop_column("products", "price_stability")
    op.drop_column("products", "buybox_price")
    op.drop_column("products", "buybox_seller")
    op.drop_column("products", "amazon_is_seller")
    op.drop_column("products", "sub_niche")
    op.drop_column("products", "niche")

    op.drop_table("search_results")
    op.drop_table("search_campaigns")
