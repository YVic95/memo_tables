# creates the chat_sessions table
# fields:
# - id (UUID, primary key) - also used as the LangGraph thread_id
# - status (string, not null) - "open" or "closed"
# - title (string, nullable)
# - created_at (datetime, not null)

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, nullable=False, default="open")
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
