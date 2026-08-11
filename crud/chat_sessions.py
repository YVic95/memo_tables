from sqlalchemy.orm import Session
from models.chat_sessions import ChatSession


def create_chat_session(db: Session) -> dict:
    session = ChatSession(status="open")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": str(session.id)}


def get_chat_session(db: Session, session_id: str) -> dict | None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return None
    return {
        "id": str(session.id),
        "status": session.status,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def close_chat_session(db: Session, session_id: str) -> bool:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session is None:
        return False
    session.status = "closed"
    db.commit()
    return True
