# Creates entity_embdeddings table.
# Fields are: 
# id (UUID), 
# entity_type (string), 
# entity_id (UUID), 
# language_id (UUID, FK to languages.id), 
# model_name (string), 
# dimensions (integer), 
# embedding (vector), 
# source_text (text), 
# created_at (datetime), 
# updated_at (datetime)
# text-embedding-ada-002 has 1536 dimensions, so we set vector(1536) for the embedding field.

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from database import Base
from datetime import datetime, timezone

class EntityEmbedding(Base):
    __tablename__ = "entity_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    model_name = Column(String, nullable=False)
    dimensions = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))
    source_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)