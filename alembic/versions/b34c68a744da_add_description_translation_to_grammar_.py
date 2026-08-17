"""add description_translation to grammar_rule_row_translations

Revision ID: b34c68a744da
Revises: 21f529b1ccb3
Create Date: 2026-08-17 16:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b34c68a744da'
down_revision: Union[str, Sequence[str], None] = '21f529b1ccb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('grammar_rule_row_translations', sa.Column('description_translation', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('grammar_rule_row_translations', 'description_translation')
