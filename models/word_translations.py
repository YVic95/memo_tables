# creates word_translations table
# fields:
# id (UUID, primary key)
# base_word_id (UUID, foreign key to base_words.id, not null)
# language_id (UUID, foreign key to languages.id, not null)
# translation (varchar, not null)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WordTranslation(Base):
    __tablename__ = "word_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_word_id = Column(UUID(as_uuid=True), ForeignKey("base_words.id"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    translation = Column(String, nullable=False)
