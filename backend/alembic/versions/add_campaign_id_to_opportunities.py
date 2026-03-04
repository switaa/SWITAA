"""add_campaign_id_to_opportunities

Revision ID: 001
Revises: None
Create Date: 2025-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("search_campaigns.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_opportunities_campaign_id", "opportunities", ["campaign_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_opportunities_campaign_id", table_name="opportunities")
    op.drop_column("opportunities", "campaign_id")
