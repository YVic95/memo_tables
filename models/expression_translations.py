# creates the expression_translations table
# fields:
# - id (UUID, primary key)
# - expression_id (UUID, foreign key to expressions.id, not null)
# - language_id (UUID, foreign key to languages.id, not null)
# - text (string, not null)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class ExpressionTranslation(Base):
    __tablename__ = "expression_translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expression_id = Column(UUID(as_uuid=True), ForeignKey("expressions.id"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    text = Column(String, nullable=False)