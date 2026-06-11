# creates expressions table
# fields are:
# id (UUID), text (string), language_id (UUID, FK to languages.id)

import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class Expression(Base):
    __tablename__ = "expressions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String, nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)