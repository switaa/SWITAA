"""add fulfillment_channel to listings

Revision ID: 005
Revises: 004
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("fulfillment_channel", sa.String(10), nullable=False, server_default="FBM"),
    )


def downgrade() -> None:
    op.drop_column("listings", "fulfillment_channel")
