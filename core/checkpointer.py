# Shared DB-backed checkpointer for LangGraph graphs.
# Uses langgraph-checkpoint-postgres against the same Postgres as the app.
# The checkpointer tables (checkpoints, checkpoint_blobs, checkpoint_writes,
# checkpoint_migrations) are created by setup() at app startup.

import os
from contextlib import ExitStack
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL_LOCAL"]

# from_conn_string is a context manager; keep its connection open for the
# process lifetime so graphs compiled at import can use the saver later.
_stack = ExitStack()
saver = _stack.enter_context(PostgresSaver.from_conn_string(DATABASE_URL))


def setup_checkpointer() -> None:
    """Create the checkpointer tables if they don't exist. Idempotent."""
    saver.setup()
