# creates language_pair table
import uuid
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class LanguagePair(Base):
    __tablename__ = "language_pairs"

    pair_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    native_language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    target_language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)