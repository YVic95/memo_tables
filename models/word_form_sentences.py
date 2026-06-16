# creates word_form_sentences table
# fields:
# id (UUID, primary key)
# word_form_id (UUID, foreign key to word_forms.id, not null)
# sentence_id (UUID, foreign key to sentences.id, not null)

import uuid
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WordFormSentence(Base):
    __tablename__ = "word_form_sentences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word_form_id = Column(UUID(as_uuid=True), ForeignKey("word_forms.id"), nullable=False)
    sentence_id = Column(UUID(as_uuid=True), ForeignKey("sentences.id"), nullable=False)
