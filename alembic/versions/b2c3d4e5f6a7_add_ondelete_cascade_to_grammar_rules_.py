"""add ondelete cascade to grammar_rules and downstream foreign keys

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sentences.grammar_rule_id → grammar_rules.id
    op.drop_constraint(
        "sentences_grammar_rule_id_fkey",
        "sentences",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_sentences_grammar_rule_id",
        "sentences",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # sentence_translations.sentence_id → sentences.id
    op.drop_constraint(
        "sentence_translations_sentence_id_fkey",
        "sentence_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_sentence_translations_sentence_id",
        "sentence_translations",
        "sentences",
        ["sentence_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # word_rule_assignments.grammar_rule_id → grammar_rules.id
    op.drop_constraint(
        "word_rule_assignments_grammar_rule_id_fkey",
        "word_rule_assignments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_word_rule_assignments_grammar_rule_id",
        "word_rule_assignments",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # word_forms.word_rule_assignment_id → word_rule_assignments.id
    op.drop_constraint(
        "word_forms_word_rule_assignment_id_fkey",
        "word_forms",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_word_forms_word_rule_assignment_id",
        "word_forms",
        "word_rule_assignments",
        ["word_rule_assignment_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # word_form_translations.word_form_id → word_forms.id
    op.drop_constraint(
        "word_form_translations_word_form_id_fkey",
        "word_form_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_word_form_translations_word_form_id",
        "word_form_translations",
        "word_forms",
        ["word_form_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # word_form_sentences.sentence_id → sentences.id
    op.drop_constraint(
        "word_form_sentences_sentence_id_fkey",
        "word_form_sentences",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_word_form_sentences_sentence_id",
        "word_form_sentences",
        "sentences",
        ["sentence_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_word_form_sentences_sentence_id",
        "word_form_sentences",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "word_form_sentences_sentence_id_fkey",
        "word_form_sentences",
        "sentences",
        ["sentence_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_word_form_translations_word_form_id",
        "word_form_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "word_form_translations_word_form_id_fkey",
        "word_form_translations",
        "word_forms",
        ["word_form_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_word_forms_word_rule_assignment_id",
        "word_forms",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "word_forms_word_rule_assignment_id_fkey",
        "word_forms",
        "word_rule_assignments",
        ["word_rule_assignment_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_word_rule_assignments_grammar_rule_id",
        "word_rule_assignments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "word_rule_assignments_grammar_rule_id_fkey",
        "word_rule_assignments",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_sentence_translations_sentence_id",
        "sentence_translations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "sentence_translations_sentence_id_fkey",
        "sentence_translations",
        "sentences",
        ["sentence_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_sentences_grammar_rule_id",
        "sentences",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "sentences_grammar_rule_id_fkey",
        "sentences",
        "grammar_rules",
        ["grammar_rule_id"],
        ["id"],
    )
