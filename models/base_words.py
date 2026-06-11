# creates the base_words table
# fields:
# - id (UUID, primary key)
# - text (string, not null)
# - language_id (UUID, foreign key to languages.id, not null)
# - word_category_id (UUID, foreign key to word_categories.id, not null)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class BaseWord(Base):
    __tablename__ = "base_words"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String, nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(UUID(as_uuid=True), ForeignKey("word_categories.id"), nullable=False)