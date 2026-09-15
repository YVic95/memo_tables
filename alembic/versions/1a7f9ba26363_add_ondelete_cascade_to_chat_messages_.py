"""add ondelete cascade to chat_messages.session_id

Revision ID: 1a7f9ba26363
Revises: 9af63d7e3eca
Create Date: 2026-09-15 11:11:55.820591

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1a7f9ba26363'
down_revision: Union[str, Sequence[str], None] = '9af63d7e3eca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_chat_messages_session_id_chat_sessions",
        "chat_messages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_chat_messages_session_id_chat_sessions",
        "chat_messages",
        "chat_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chat_messages_session_id_chat_sessions",
        "chat_messages",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_chat_messages_session_id_chat_sessions",
        "chat_messages",
        "chat_sessions",
        ["session_id"],
        ["id"],
    )
