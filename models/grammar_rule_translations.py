# creates grammar_rule_translations table
# fields:
# id (UUID, primary key)
# grammar_rule_id (UUID, foreign key to grammar_rules.id, not null)
# language_id (UUID, foreign key to languages.id, not null)
# name (varchar, not null)
# description (text, nullable)

import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class GrammarRuleTranslation(Base):
    __tablename__ = "grammar_rule_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grammar_rule_id = Column(UUID(as_uuid=True), ForeignKey("grammar_rules.id", ondelete="CASCADE"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
