# creates topics table
# fields are:
# id (UUID), name (string), 
# description (text), language_id (UUID, FK to languages.id)

import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class Topic(Base):
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)