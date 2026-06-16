# creates word_form_translations table
# fields:
# id (UUID, primary key)
# word_form_id (UUID, foreign key to word_forms.id, not null)
# language_id (UUID, foreign key to languages.id, not null)
# translation (varchar, not null)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WordFormTranslation(Base):
    __tablename__ = "word_form_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word_form_id = Column(UUID(as_uuid=True), ForeignKey("word_forms.id"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    translation = Column(String, nullable=False)
