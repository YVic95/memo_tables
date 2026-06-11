# creates word_categories table
# fields: id (UUID), name (string), slug (string, unique)

import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class WordCategory(Base):
    __tablename__ = "word_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)