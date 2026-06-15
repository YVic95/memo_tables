# creates base_word_topics table
# fields:
# base_word_id (UUID, foreign key to base_words.id, not null)
# topic_id (UUID, foreign key to topics.id, not null)

from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class BaseWordTopic(Base):
    __tablename__ = "base_word_topics"

    base_word_id = Column(UUID(as_uuid=True), ForeignKey("base_words.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("base_word_id", "topic_id"),
    )