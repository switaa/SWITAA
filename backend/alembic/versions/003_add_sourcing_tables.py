"""add sourcing_searches and sourcing_results tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sourcing_searches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("search_type", sa.String(50), nullable=False, server_default="web"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_products", sa.Integer, nullable=False, server_default="0"),
        sa.Column("products_checked", sa.Integer, nullable=False, server_default="0"),
        sa.Column("matches_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("profitable_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("config", JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=False, server_default=""),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_sourcing_searches_status", "sourcing_searches", ["status"])

    op.create_table(
        "sourcing_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("search_id", UUID(as_uuid=True), sa.ForeignKey("sourcing_searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asin", sa.String(10), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("source_url", sa.Text, nullable=False, server_default=""),
        sa.Column("source_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("source_price_ht", sa.Numeric(10, 2), nullable=True),
        sa.Column("source_shipping", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("source_currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column("source_title", sa.String(500), nullable=False, server_default=""),
        sa.Column("source_in_stock", sa.Boolean, nullable=True),
        sa.Column("amazon_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("referral_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("fulfillment_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("net_profit", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("margin_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("roi_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("match_type", sa.String(20), nullable=False, server_default="asin"),
        sa.Column("match_confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("raw_data", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sourcing_results_search_id", "sourcing_results", ["search_id"])
    op.create_index("ix_sourcing_results_product_id", "sourcing_results", ["product_id"])
    op.create_index("ix_sourcing_results_asin", "sourcing_results", ["asin"])


def downgrade() -> None:
    op.drop_table("sourcing_results")
    op.drop_table("sourcing_searches")
