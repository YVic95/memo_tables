"""add workflow_step to chat_sessions

Revision ID: 5d14e229afb7
Revises: 1a7f9ba26363
Create Date: 2026-09-15 11:54:16.859766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5d14e229afb7'
down_revision: Union[str, Sequence[str], None] = '1a7f9ba26363'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('workflow_step', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'workflow_step')