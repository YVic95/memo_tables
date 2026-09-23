import asyncio
import uuid
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from unittest.mock import MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base
from models.language import Language
from models.language_pairs import LanguagePair
from routers.create_rule_agent import (
    ProposeMissingRulesRequest,
    InitialRuleRequest,
    call_agent,
)


def _call_agent(body, db):
    return asyncio.run(call_agent(body, db))


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def pair(db_session):
    lang_en = Language(code="en", name="English")
    lang_es = Language(code="es", name="Spanish")
    db_session.add_all([lang_en, lang_es])
    db_session.commit()
    db_session.refresh(lang_en)
    db_session.refresh(lang_es)

    pair = LanguagePair(native_language_id=lang_en.id, target_language_id=lang_es.id)
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)

    return {
        "pair_id": pair.pair_id,
        "native_language_id": lang_en.id,
        "target_language_id": lang_es.id,
        "native_name": "English",
        "target_name": "Spanish",
    }


def _make_request(pair_id, type="propose_missing_rules"):
    return ProposeMissingRulesRequest(type="propose_missing_rules", language_pair_id=pair_id)


class TestProposeMissingRules:
    @pytest.fixture()
    def mock_graph(self, monkeypatch):
        mock = MagicMock()
        monkeypatch.setattr("routers.create_rule_agent.propose_rules_graph", mock)
        return mock

    def test_unknown_language_pair_returns_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            _call_agent(_make_request(uuid.uuid4()), db_session)
        assert exc_info.value.status_code == 404

    def test_returns_rules_and_message_from_graph(self, pair, mock_graph, db_session):
        mock_graph.invoke.return_value = {
            "proposed_rules": [
                {
                    "title": "Present tense -ar",
                    "explanation": "Conjugate -ar verbs.",
                    "canonical_rule_id": str(uuid.uuid4()),
                }
            ],
            "message": "",
        }

        result = _call_agent(_make_request(pair["pair_id"]), db_session)

        assert result["rules"] == mock_graph.invoke.return_value["proposed_rules"]
        assert result["message"] == ""

    def test_invokes_graph_with_db_and_resolved_pair(self, pair, mock_graph, db_session):
        mock_graph.invoke.return_value = {"proposed_rules": [], "message": ""}

        _call_agent(_make_request(pair["pair_id"]), db_session)

        state = mock_graph.invoke.call_args.args[0]
        assert state["db"] is db_session
        assert state["native_language_id"] == pair["native_language_id"]
        assert state["target_language_id"] == pair["target_language_id"]
        assert state["native_language"] == "English"
        assert state["target_language"] == "Spanish"

    def test_propagates_empty_rules_and_message_for_exhausted_pair(self, pair, mock_graph, db_session):
        mock_graph.invoke.return_value = {
            "proposed_rules": [],
            "message": "All rules in the catalog for this language pair have already been created. No missing rules to suggest.",
        }

        result = _call_agent(_make_request(pair["pair_id"]), db_session)

        assert result["rules"] == []
        assert "already been created" in result["message"]


async def _collect_events(response):
    events = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode()
        events.append(chunk)
    return events


class TestInitialRule:
    @pytest.fixture()
    def mock_graph(self, monkeypatch, db_session):
        mock = MagicMock()
        mock.stream.return_value = [
            {"copy_canonical_category": {"word_category_id": uuid.uuid4()}},
            {"persist_rule": {"grammar_rule_id": uuid.uuid4()}},
            {"translate_rule": {}},
            {"persist_translation": {}},
            {"generate_content": {"grammar_rule_id": uuid.uuid4(), "full_content": "## Rule"}},
        ]
        monkeypatch.setattr("routers.create_rule_agent.initial_rule_graph", mock)
        monkeypatch.setattr("routers.create_rule_agent.SessionLocal", lambda: db_session)
        return mock

    def _initial_request(self, pair_id, **overrides):
        payload = {
            "type": "initial_rule",
            "language_pair_id": pair_id,
            "title": "Present tense -ar",
            "explanation": "Conjugate -ar verbs.",
            "canonical_rule_id": uuid.uuid4(),
        }
        payload.update(overrides)
        return InitialRuleRequest(**payload)

    def test_unknown_language_pair_returns_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            _call_agent(self._initial_request(uuid.uuid4()), db_session)
        assert exc_info.value.status_code == 404

    def test_requires_canonical_rule_id(self, pair, db_session):
        with pytest.raises(ValidationError):
            self._initial_request(pair["pair_id"], canonical_rule_id=None)

    def test_requires_title_and_explanation(self, pair, db_session):
        with pytest.raises(ValidationError):
            self._initial_request(pair["pair_id"], title=None)

    def test_passes_canonical_rule_id_into_the_graph(
        self, pair, mock_graph, db_session
    ):
        request = self._initial_request(pair["pair_id"])
        response = _call_agent(request, db_session)
        asyncio.run(_collect_events(response))

        graph_input = mock_graph.stream.call_args.args[0]
        assert graph_input["canonical_rule_id"] == request.canonical_rule_id

    def test_streams_creation_progress_including_catalog_copy(
        self, pair, mock_graph, db_session
    ):
        response = _call_agent(self._initial_request(pair["pair_id"]), db_session)
        events = asyncio.run(_collect_events(response))
        payload = "".join(events)

        assert 'event: node_start' in payload
        assert '"node": "copy_canonical_category"' in payload
        assert '"node": "generate_content"' in payload
        assert 'event: done' in payload