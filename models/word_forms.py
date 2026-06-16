# creates word_forms table
# fields:
# id (UUID, primary key)
# word_rule_assignment_id (UUID, foreign key to word_rule_assignments.id, not null)
# grammar_rule_row_id (UUID, foreign key to grammar_rule_rows.id, not null)
# form (varchar, not null)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WordForm(Base):
    __tablename__ = "word_forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word_rule_assignment_id = Column(UUID(as_uuid=True), ForeignKey("word_rule_assignments.id"), nullable=False)
    grammar_rule_row_id = Column(UUID(as_uuid=True), ForeignKey("grammar_rule_rows.id"), nullable=False)
    form = Column(String, nullable=False)
