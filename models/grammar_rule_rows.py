# creates grammar_rule_rows table
# fields:
# id (UUID, primary key)
# grammar_rule_id (UUID, foreign key to grammar_rules.id, not null)
# label (varchar, not null)
# position (int, not null)

import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class GrammarRuleRow(Base):
    __tablename__ = "grammar_rule_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grammar_rule_id = Column(UUID(as_uuid=True), ForeignKey("grammar_rules.id"), nullable=False)
    label = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
