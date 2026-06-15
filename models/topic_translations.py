# creates topic_translations table
# fields:
# id (UUID, primary key)
# topic_id (UUID, foreign key to topics.id, not null)
# language_id (UUID, foreign key to languages.id, not null)
# name (String, not null)
# description (Text, nullable)

import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class TopicTranslation(Base):
    __tablename__ = "topic_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)