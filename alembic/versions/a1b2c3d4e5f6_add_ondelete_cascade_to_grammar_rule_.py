"""add ondelete cascade to grammar_rule_rows foreign keys

Revision ID: a1b2c3d4e5f6
Revises: 6b680c74653d
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6b680c74653d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "grammar_rule_rows_grammar_rule_id_fkey",
        "grammar_rule_rows",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_grammar_rule_rows_grammar_rule_id",
        "grammar_rule_rows",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "grammar_rule_row_translations_grammar_rule_row_id_fkey",
        "grammar_rule_row_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_grammar_rule_row_translations_grammar_rule_row_id",
        "grammar_rule_row_translations",
        "grammar_rule_rows",
        ["grammar_rule_row_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "word_forms_grammar_rule_row_id_fkey",
        "word_forms",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_word_forms_grammar_rule_row_id",
        "word_forms",
        "grammar_rule_rows",
        ["grammar_rule_row_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_word_forms_grammar_rule_row_id",
        "word_forms",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "word_forms_grammar_rule_row_id_fkey",
        "word_forms",
        "grammar_rule_rows",
        ["grammar_rule_row_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_grammar_rule_row_translations_grammar_rule_row_id",
        "grammar_rule_row_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "grammar_rule_row_translations_grammar_rule_row_id_fkey",
        "grammar_rule_row_translations",
        "grammar_rule_rows",
        ["grammar_rule_row_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_grammar_rule_rows_grammar_rule_id",
        "grammar_rule_rows",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "grammar_rule_rows_grammar_rule_id_fkey",
        "grammar_rule_rows",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
    )
