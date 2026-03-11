"""add sku, marketplace_status, last_push_at to listings

Revision ID: 004
Revises: 003
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("sku", sa.String(255), nullable=False, server_default=""))
    op.add_column("listings", sa.Column("marketplace_status", sa.String(30), nullable=False, server_default="not_pushed"))
    op.add_column("listings", sa.Column("last_push_at", sa.DateTime, nullable=True))
    op.create_index("ix_listings_sku", "listings", ["sku"])
    op.create_index("ix_listings_marketplace_status", "listings", ["marketplace_status"])


def downgrade() -> None:
    op.drop_index("ix_listings_marketplace_status", table_name="listings")
    op.drop_index("ix_listings_sku", table_name="listings")
    op.drop_column("listings", "last_push_at")
    op.drop_column("listings", "marketplace_status")
    op.drop_column("listings", "sku")
