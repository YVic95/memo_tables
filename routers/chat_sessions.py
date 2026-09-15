import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.chat_sessions import create_chat_session, get_active_chat_session, get_chat_session, set_workflow_step
from graphs.models import WorkflowStepUpdate

router = APIRouter(tags=["chat-sessions"])

@router.post("/api/chat-sessions")
def create_session(db: Annotated[Session, Depends(get_db)]):
    return create_chat_session(db)

@router.get("/api/chat-sessions/active")
def active_session(db: Annotated[Session, Depends(get_db)]):
    return get_active_chat_session(db)

@router.patch("/api/chat-sessions/{session_id}")
def update_session(session_id: uuid.UUID, body: WorkflowStepUpdate, db: Annotated[Session, Depends(get_db)]):
    session = get_chat_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return set_workflow_step(db, session_id, body.workflow_step)
