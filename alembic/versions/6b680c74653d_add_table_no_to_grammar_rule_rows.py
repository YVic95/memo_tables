"""add table_no to grammar_rule_rows

Revision ID: 6b680c74653d
Revises: b34c68a744da
Create Date: 2026-08-17 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b680c74653d'
down_revision: Union[str, Sequence[str], None] = 'b34c68a744da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('grammar_rule_rows', sa.Column('table_no', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('grammar_rule_rows', 'table_no')
