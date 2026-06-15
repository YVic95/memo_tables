# create sentence_translations table
# fields:
# id (UUID, primary key)
# sentence_id (UUID, foreign key to sentences.id, not null)
# language_id (UUID, foreign key to languages.id, not null)
# template (Text, not null) - the translated sentence template

import uuid
from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class SentenceTranslation(Base):
    __tablename__ = "sentence_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sentence_id = Column(UUID(as_uuid=True), ForeignKey("sentences.id"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    template = Column(Text, nullable=False)