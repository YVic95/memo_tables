import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.chat_sessions import create_chat_session, get_active_chat_session, get_chat_session, set_workflow_step, set_chat_session_title, close_chat_session
from crud.language_pairs import get_language_pair_by_id
from graphs.models import ChatSessionUpdate

router = APIRouter(tags=["chat-sessions"])

@router.post("/api/chat-sessions")
def create_session(db: Annotated[Session, Depends(get_db)]):
    return create_chat_session(db)

@router.get("/api/chat-sessions/active")
def active_session(db: Annotated[Session, Depends(get_db)]):
    return get_active_chat_session(db)

@router.patch("/api/chat-sessions/{session_id}")
def update_session(session_id: uuid.UUID, body: ChatSessionUpdate, db: Annotated[Session, Depends(get_db)]):
    session = get_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if body.language_pair_id is not None and body.rule_title:
        pair = get_language_pair_by_id(db, body.language_pair_id)
        if pair is None:
            raise HTTPException(status_code=404, detail="Language pair not found")
        title = f"{pair['native_name']} → {pair['target_name']}: {body.rule_title}"
        session = set_chat_session_title(db, session_id, title)

    if body.workflow_step is not None:
        session = set_workflow_step(db, session_id, body.workflow_step)

    return session or get_chat_session(db, session_id)

@router.post("/api/chat-sessions/{session_id}/close")
def close_session(session_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]):
    session = get_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    close_chat_session(db, session_id)
    return {"status": "closed"}
