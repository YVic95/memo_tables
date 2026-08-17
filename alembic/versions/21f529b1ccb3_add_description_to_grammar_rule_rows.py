"""add description to grammar_rule_rows

Revision ID: 21f529b1ccb3
Revises: facd7f477c9a
Create Date: 2026-08-17 16:09:59.304937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21f529b1ccb3'
down_revision: Union[str, Sequence[str], None] = 'facd7f477c9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('grammar_rule_rows', sa.Column('description', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('grammar_rule_rows', 'description')
