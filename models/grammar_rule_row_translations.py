# creates grammar_rule_row_translations table
# fields:
# id (UUID, primary key)
# grammar_rule_row_id (UUID, foreign key to grammar_rule_rows.id, not null)
# language_id (UUID, foreign key to languages.id, not null)
# label_translation (varchar, not null)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class GrammarRuleRowTranslation(Base):
    __tablename__ = "grammar_rule_row_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grammar_rule_row_id = Column(UUID(as_uuid=True), ForeignKey("grammar_rule_rows.id"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    label_translation = Column(String, nullable=False)
