import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from crud.chat_messages import create_chat_message, get_chat_messages
from crud.chat_sessions import get_chat_session
from graphs.models import ChatMessageRequest

router = APIRouter(tags=["chat-messages"])

@router.post("/api/chat-messages")
def create_message(body: ChatMessageRequest, db: Annotated[Session, Depends(get_db)]):
    session = get_chat_session(db, body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return create_chat_message(db, body.session_id, body.role, body.message_type, body.content)

@router.get("/api/chat-sessions/{session_id}/messages")
def list_messages(session_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]):
    session = get_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return get_chat_messages(db, session_id)