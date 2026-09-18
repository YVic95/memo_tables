# creates canonical_rules table
# fields:
# - id (UUID, primary key)
# - native_language_id (UUID, foreign key to languages.id, not null)
# - target_language_id (UUID, foreign key to languages.id, not null)
# - word_category_id (UUID, foreign key to word_categories.id, not null)
# - level (string, not null, one of CEFR A1-C2)
# - name (string, not null, written in the native language)
# - description (text, not null, written in the native language)
# - position (int, not null)
# - slug (string, not null)
# - is_active (bool, not null, default true)

import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class CanonicalRule(Base):
    __tablename__ = "canonical_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    native_language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    target_language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(UUID(as_uuid=True), ForeignKey("word_categories.id"), nullable=False)
    level = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    slug = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "native_language_id",
            "target_language_id",
            "slug",
            name="uq_canonical_rules_pair_slug",
        ),
        CheckConstraint(
            "level IN ('A1','A2','B1','B2','C1','C2')",
            name="ck_canonical_rules_level_cefr",
        ),
    )