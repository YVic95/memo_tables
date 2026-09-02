"""add ondelete cascade to word_translations.base_word_id

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "word_translations_base_word_id_fkey",
        "word_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_word_translations_base_word_id",
        "word_translations",
        "base_words",
        ["base_word_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_word_translations_base_word_id",
        "word_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "word_translations_base_word_id_fkey",
        "word_translations",
        "base_words",
        ["base_word_id"],
        ["id"],
    )
