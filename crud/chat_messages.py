import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from models.chat_messages import ChatMessage
from graphs.models import MessageRole, MessageType
from sqlalchemy.exc import IntegrityError

def _serialize_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "session_id": message.session_id,
        "role": message.role,
        "message_type": message.message_type,
        "content": message.content,
        "position": message.position,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }

def create_chat_message(
    db: Session,
    session_id: uuid.UUID,
    role: MessageRole,
    message_type: MessageType,
    content: dict,
) -> dict:
    next_position_subquery = (
        select(func.coalesce(func.max(ChatMessage.position), 0) + 1)
        .where(ChatMessage.session_id == session_id)
        .scalar_subquery()
    )

    message = ChatMessage(
        session_id=session_id,
        role=role,
        message_type=message_type,
        content=content,
        position=next_position_subquery,
    )
    db.add(message)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(message)
    return _serialize_message(message)

def get_chat_messages(
    db: Session, 
    session_id: uuid.UUID
) -> list[dict]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.position)
        .all()
    )
    return [_serialize_message(message) for message in messages]