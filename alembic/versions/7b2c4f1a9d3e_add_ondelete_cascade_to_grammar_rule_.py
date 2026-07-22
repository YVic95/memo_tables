"""add ondelete cascade to grammar_rule_translations.grammar_rule_id

Revision ID: 7b2c4f1a9d3e
Revises: e19f110fd978
Create Date: 2026-07-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7b2c4f1a9d3e'
down_revision: Union[str, Sequence[str], None] = 'e19f110fd978'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "grammar_rule_translations_grammar_rule_id_fkey",
        "grammar_rule_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_grammar_rule_translations_grammar_rule_id",
        "grammar_rule_translations",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_grammar_rule_translations_grammar_rule_id",
        "grammar_rule_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "grammar_rule_translations_grammar_rule_id_fkey",
        "grammar_rule_translations",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
    )
