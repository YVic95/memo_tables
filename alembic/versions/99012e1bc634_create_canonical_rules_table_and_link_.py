"""create canonical_rules table and link grammar_rules

Revision ID: 99012e1bc634
Revises: 5d14e229afb7
Create Date: 2026-09-18 11:35:38.942295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99012e1bc634'
down_revision: Union[str, Sequence[str], None] = '5d14e229afb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('canonical_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('native_language_id', sa.UUID(), nullable=False),
    sa.Column('target_language_id', sa.UUID(), nullable=False),
    sa.Column('word_category_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.CheckConstraint("level IN ('A1','A2','B1','B2','C1','C2')", name='ck_canonical_rules_level_cefr'),
    sa.ForeignKeyConstraint(['native_language_id'], ['languages.id'], ),
    sa.ForeignKeyConstraint(['target_language_id'], ['languages.id'], ),
    sa.ForeignKeyConstraint(['word_category_id'], ['word_categories.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('native_language_id', 'target_language_id', 'slug', name='uq_canonical_rules_pair_slug')
    )

    op.add_column('grammar_rules', sa.Column('canonical_rule_id', sa.UUID(), sa.ForeignKey('canonical_rules.id', name='grammar_rules_canonical_rule_id_fkey'), nullable=False))
    op.create_unique_constraint('uq_grammar_rules_canonical_rule_id', 'grammar_rules', ['canonical_rule_id'])

    op.create_index(
        'ix_grammar_rules_name_trgm',
        'grammar_rules',
        ['name'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'name': 'gin_trgm_ops'},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_grammar_rules_name_trgm', table_name='grammar_rules')
    op.drop_constraint('grammar_rules_canonical_rule_id_fkey', 'grammar_rules', type_='foreignkey')
    op.drop_constraint('uq_grammar_rules_canonical_rule_id', 'grammar_rules', type_='unique')
    op.drop_column('grammar_rules', 'canonical_rule_id')
    op.drop_table('canonical_rules')
