"""drop unique constraint on grammar_rules.canonical_rule_id

Revision ID: b7e1a94d6c02
Revises: 99012e1bc634
Create Date: 2026-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7e1a94d6c02'
down_revision: Union[str, Sequence[str], None] = '99012e1bc634'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # A UNIQUE constraint owns its backing index in Postgres, so dropping the
    # constraint drops the index with it. Nothing else references that index.
    # See the `canonical_rule_id` note in models/grammar_rules.py for why the
    # relation is many-to-one.
    op.drop_constraint(
        'uq_grammar_rules_canonical_rule_id', 'grammar_rules', type_='unique'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Fails if two rules already share a catalog entry, which is exactly the
    # data the constraint used to forbid.
    op.create_unique_constraint(
        'uq_grammar_rules_canonical_rule_id', 'grammar_rules', ['canonical_rule_id']
    )
