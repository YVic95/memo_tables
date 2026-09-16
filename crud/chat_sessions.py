import uuid
from sqlalchemy.orm import Session
from models.chat_sessions import ChatSession

def create_chat_session(db: Session) -> dict:
    session = ChatSession(status="open")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id}

def _serialize_session(session: ChatSession) -> dict:
    return {
        "id": session.id,
        "status": session.status,
        "title": session.title,
        "workflow_step": session.workflow_step,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }

def get_chat_session(db: Session, session_id: uuid.UUID) -> dict | None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return None
    return _serialize_session(session)

def get_active_chat_session(db: Session) -> dict | None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.status == "open")
        .order_by(ChatSession.created_at.desc())
        .first()
    )
    if session is None:
        return None
    return _serialize_session(session)

def set_workflow_step(db: Session, session_id: uuid.UUID, workflow_step: str | None) -> dict | None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return None
    session.workflow_step = workflow_step
    db.commit()
    return _serialize_session(session)

def set_chat_session_title(db: Session, session_id: uuid.UUID, title: str) -> dict | None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return None
    session.title = title
    db.commit()
    return _serialize_session(session)

def close_chat_session(db: Session, session_id: uuid.UUID) -> bool:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return False
    session.status = "closed"
    db.commit()
    return True
