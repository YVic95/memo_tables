# creates expression_topic table for many-to-many relationship between expressions and topics
# fields:
# expression_id (UUID, foreign key to expressions.id, not null)
# topic_id (UUID, foreign key to topics.id, not null)

from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class ExpressionTopic(Base):
    __tablename__ = "expression_topics"

    expression_id = Column(UUID(as_uuid=True), ForeignKey("expressions.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("expression_id", "topic_id"),
    )