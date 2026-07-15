"""seed grammar categories for words

Revision ID: e19f110fd978
Revises: eb4d837ee312
Create Date: 2026-07-15 16:47:36.065454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e19f110fd978'
down_revision: Union[str, Sequence[str], None] = 'eb4d837ee312'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = [
    ("Noun", "noun"),
    ("Verb", "verb"),
    ("Adjective", "adjective"),
    ("Adverb", "adverb"),
    ("Pronoun", "pronoun"),
    ("Preposition", "preposition"),
    ("Conjunction", "conjunction"),
    ("Interjection", "interjection"),
    ("Article", "article"),
    ("Numeral", "numeral"),
    ("Determiner", "determiner"),
]

def upgrade() -> None:
    values_sql = ", ".join(
        f"(gen_random_uuid(), '{name}', '{slug}')" for name, slug in CATEGORIES
    )
    op.execute(
        f"""
        INSERT INTO word_categories (id, name, slug)
        VALUES {values_sql}
        ON CONFLICT (slug) DO NOTHING;
        """
    )

def downgrade() -> None:
    slugs = ", ".join(f"'{slug}'" for _, slug in CATEGORIES)
    op.execute(
        f"""
        DELETE FROM word_categories
        WHERE slug IN ({slugs});
        """
    )
