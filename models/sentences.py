# creates the senteces table
# fields:
# id (UUID, primary key)
# template (Text, not null)
# language_id (UUID, foreign key to languages.id, not null)
# word_category_id (UUID, foreign key to word_categories.id, not null)
# grammar_rule_id (UUID, foreign key to grammar_rules.id, not null)
# row_position (Integer, not null) - the position of the sentence template in the list

import uuid
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class Sentence(Base):
    __tablename__ = "sentences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template = Column(Text, nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(UUID(as_uuid=True), ForeignKey("word_categories.id"), nullable=False)
    grammar_rule_id = Column(UUID(as_uuid=True), ForeignKey("grammar_rules.id"), nullable=False)
    row_position = Column(Integer, nullable=False)