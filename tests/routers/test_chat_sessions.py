import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from models.chat_sessions import ChatSession
from models.language import Language
from models.language_pairs import LanguagePair
from serve import app

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

def _visit_JSONB(self, type_, **kw):
    return "TEXT"

SQLiteTypeCompiler.visit_JSONB = _visit_JSONB


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    session.close()


@pytest.fixture()
def open_session(db_session):
    session = ChatSession(status="open")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture()
def closed_session(db_session):
    session = ChatSession(status="closed")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture()
def language_pair_es_en(db_session):
    lang_es = Language(code="es", name="Spanish")
    lang_en = Language(code="en", name="English")
    db_session.add_all([lang_es, lang_en])
    db_session.commit()
    db_session.refresh(lang_es)
    db_session.refresh(lang_en)

    pair = LanguagePair(native_language_id=lang_es.id, target_language_id=lang_en.id)
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)
    return {"pair_id": pair.pair_id}


class TestCloseSession:
    def test_close_open_session_sets_status(self, db_session, open_session):
        client = TestClient(app)
        resp = client.post(f"/api/chat-sessions/{open_session.id}/close")
        assert resp.status_code == 200
        assert resp.json() == {"status": "closed"}

        refreshed = db_session.query(ChatSession).filter(ChatSession.id == open_session.id).first()
        assert refreshed.status == "closed"

    def test_close_nonexistent_session_returns_404(self, db_session):
        client = TestClient(app)
        fake_id = uuid.uuid4()
        resp = client.post(f"/api/chat-sessions/{fake_id}/close")
        assert resp.status_code == 404

    def test_close_already_closed_session(self, db_session, closed_session):
        client = TestClient(app)
        resp = client.post(f"/api/chat-sessions/{closed_session.id}/close")
        assert resp.status_code == 200
        assert resp.json() == {"status": "closed"}


class TestActiveSessionExcludesClosed:
    def test_active_session_returns_open(self, db_session, open_session):
        client = TestClient(app)
        resp = client.get("/api/chat-sessions/active")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(open_session.id)
        assert data["status"] == "open"

    def test_active_session_returns_none_when_all_closed(self, db_session, closed_session):
        client = TestClient(app)
        resp = client.get("/api/chat-sessions/active")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_active_session_returns_most_recent_open(self, db_session):
        older = ChatSession(status="open")
        newer = ChatSession(status="open")
        db_session.add_all([older, newer])
        db_session.commit()
        db_session.refresh(older)
        db_session.refresh(newer)

        client = TestClient(app)
        resp = client.get("/api/chat-sessions/active")
        assert resp.json()["id"] == str(newer.id)

    def test_closed_session_not_returned_by_active(self, db_session, closed_session):
        client = TestClient(app)
        resp = client.get("/api/chat-sessions/active")
        assert resp.json() is None


class TestTitle:
    def test_patch_with_pair_and_rule_sets_combined_title(self, db_session, open_session, language_pair_es_en):
        client = TestClient(app)
        resp = client.patch(
            f"/api/chat-sessions/{open_session.id}",
            json={
                "language_pair_id": str(language_pair_es_en["pair_id"]),
                "rule_title": "Noun Gender",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Spanish → English: Noun Gender"

        refreshed = db_session.query(ChatSession).filter(ChatSession.id == open_session.id).first()
        assert refreshed.title == "Spanish → English: Noun Gender"

    def test_patch_with_unknown_pair_returns_404(self, db_session, open_session):
        client = TestClient(app)
        resp = client.patch(
            f"/api/chat-sessions/{open_session.id}",
            json={"language_pair_id": str(uuid.uuid4()), "rule_title": "Noun Gender"},
        )
        assert resp.status_code == 404

    def test_patch_workflow_only_leaves_title_null(self, db_session, open_session):
        client = TestClient(app)
        resp = client.patch(
            f"/api/chat-sessions/{open_session.id}",
            json={"workflow_step": "rule_saved"},
        )
        assert resp.status_code == 200
        assert resp.json()["workflow_step"] == "rule_saved"
        assert resp.json()["title"] is None

        refreshed = db_session.query(ChatSession).filter(ChatSession.id == open_session.id).first()
        assert refreshed.title is None
        assert refreshed.workflow_step == "rule_saved"


class TestChatMessagePersistence:
    def test_skeleton_table_replacement_persists_and_roundtrips(self, db_session, open_session):
        client = TestClient(app)
        markdown = "| Label | Verb: hablar |\n| --- | --- |\n| 1st | hablo |"
        resp = client.post(
            "/api/chat-messages",
            json={
                "session_id": str(open_session.id),
                "role": "assistant",
                "message_type": "skeleton_table_replacement",
                "content": {"category": "verbs", "markdown": markdown},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message_type"] == "skeleton_table_replacement"
        assert data["content"] == {"category": "verbs", "markdown": markdown}

        msgs = client.get(f"/api/chat-sessions/{open_session.id}/messages").json()
        assert any(
            m["message_type"] == "skeleton_table_replacement"
            and m["content"]["category"] == "verbs"
            for m in msgs
        )
