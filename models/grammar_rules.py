# creates the grammar_rules table
# fields:
# - id (UUID, primary key)
# - name (string, not null)
# - description (text, nullable)
# - language_id (UUID, foreign key to languages.id, not null)
# - word_category_id (UUID, foreign key to word_categories.id, not null)
# - canonical_rule_id (UUID, foreign key to canonical_rules.id, not null)
#
# The relation is many-to-one: one catalog entry can back several rules, at
# different levels of detail. The duplicate warning is what guards against
# creating the same rule twice.

import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class GrammarRule(Base):
    __tablename__ = "grammar_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(UUID(as_uuid=True), ForeignKey("word_categories.id"), nullable=False)
    canonical_rule_id = Column(UUID(as_uuid=True), ForeignKey("canonical_rules.id"), nullable=False)

    __table_args__ = (
        Index(
            "ix_grammar_rules_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )