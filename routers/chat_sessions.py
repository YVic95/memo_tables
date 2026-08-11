from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.chat_sessions import create_chat_session

router = APIRouter(tags=["chat-sessions"])

@router.post("/api/chat-sessions")
def create_session(db: Annotated[Session, Depends(get_db)]):
    return create_chat_session(db)
