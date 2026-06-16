# creates word_rule_assignments table
# fields:
# id (UUID, primary key)
# base_word_id (UUID, foreign key to base_words.id, not null)
# grammar_rule_id (UUID, foreign key to grammar_rules.id, not null)

import uuid
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WordRuleAssignment(Base):
    __tablename__ = "word_rule_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_word_id = Column(UUID(as_uuid=True), ForeignKey("base_words.id"), nullable=False)
    grammar_rule_id = Column(UUID(as_uuid=True), ForeignKey("grammar_rules.id"), nullable=False)
