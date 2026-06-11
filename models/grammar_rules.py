# creates the grammar_rules table
# fields:
# - id (UUID, primary key)
# - name (string, not null)
# - description (text, nullable)
# - language_id (UUID, foreign key to languages.id, not null)
# - word_category_id (UUID, foreign key to word_categories.id, not null)

import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class GrammarRule(Base):
    __tablename__ = "grammar_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(UUID(as_uuid=True), ForeignKey("word_categories.id"), nullable=False)