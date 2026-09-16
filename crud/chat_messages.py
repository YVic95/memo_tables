import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from models.chat_messages import ChatMessage
from models.chat_sessions import ChatSession
from graphs.models import MessageRole, MessageType

def _strip_nulls(obj):
    if isinstance(obj, str):
        return obj.replace("\x00", "")
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_nulls(item) for item in obj]
    return obj


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
    # Locks the session row for the rest of this transaction. Any other
    # transaction trying to do the same for this session_id blocks here
    # until this one commits/rolls back — that's what serializes the
    # position calculation below and prevents the collision.
    db.execute(
        select(ChatSession.id).where(ChatSession.id == session_id).with_for_update()
    )

    next_position = db.execute(
        select(func.coalesce(func.max(ChatMessage.position), 0) + 1)
        .where(ChatMessage.session_id == session_id)
    ).scalar_one()

    content = _strip_nulls(content)

    message = ChatMessage(
        session_id=session_id,
        role=role,
        message_type=message_type,
        content=content,
        position=next_position,
    )
    db.add(message)
    db.commit()
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