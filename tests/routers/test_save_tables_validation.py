import uuid
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base
from models.language import Language
from models.language_pairs import LanguagePair
from models.word_categories import WordCategory
from models.grammar_rules import GrammarRule
from graphs.models import SaveTablesRequest
from routers.save_tables_agent import save_tables


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
def seed_data(db_session):
    lang_es = Language(code="es", name="Spanish")
    lang_en = Language(code="en", name="English")
    db_session.add_all([lang_es, lang_en])
    db_session.commit()
    db_session.refresh(lang_es)
    db_session.refresh(lang_en)

    pair = LanguagePair(
        native_language_id=lang_es.id,
        target_language_id=lang_en.id,
    )
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)

    cat = WordCategory(name="Nouns", slug="nouns")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    rule = GrammarRule(
        name="Noun Gender",
        description="Masculine vs feminine",
        language_id=lang_es.id,
        word_category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    return {
        "pair_id": str(pair.pair_id),
        "rule_id": str(rule.id),
    }


def _make_request(seed_data, **overrides):
    defaults = {
        "language_pair_id": seed_data["pair_id"],
        "session_id": str(uuid.uuid4()),
        "grammar_rule_id": seed_data["rule_id"],
        "tables": [
            {
                "title": "Noun Gender",
                "headers": ["Form", "Example"],
                "rows": [
                    {"cells": ["Masculine", "el gato"]},
                    {"cells": ["Feminine", "la gata"]},
                ],
            }
        ],
    }
    defaults.update(overrides)
    return SaveTablesRequest(**defaults)


class TestGrammarRuleExists:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_missing_grammar_rule_returns_400(self, mock_get_rule, mock_get_pair, db_session, seed_data):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = None
        body = _make_request(seed_data, grammar_rule_id=str(uuid.uuid4()))

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)
        assert exc_info.value.status_code == 400
        assert "grammar rule" in exc_info.value.detail.lower()


class TestTablesListNotEmpty:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_empty_tables_returns_400(self, mock_get_rule, mock_get_pair, db_session, seed_data):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.UUID(seed_data["rule_id"]),
            name="test",
            description="test",
            language_id="1",
            word_category_id="1",
        )
        body = _make_request(seed_data, tables=[])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)
        assert exc_info.value.status_code == 400
        assert "tables" in exc_info.value.detail.lower()


class TestTableHasRows:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_table_with_no_rows_returns_400(self, mock_get_rule, mock_get_pair, db_session, seed_data):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.UUID(seed_data["rule_id"]),
            name="test",
            description="test",
            language_id="1",
            word_category_id="1",
        )
        body = _make_request(seed_data, tables=[
            {"title": "Empty", "headers": ["A"], "rows": []}
        ])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)
        assert exc_info.value.status_code == 400
        assert "row" in exc_info.value.detail.lower()


class TestRowCellCountMatchesHeaders:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_row_too_many_cells_returns_400(self, mock_get_rule, mock_get_pair, db_session, seed_data):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.UUID(seed_data["rule_id"]),
            name="test",
            description="test",
            language_id="1",
            word_category_id="1",
        )
        body = _make_request(seed_data, tables=[
            {"title": "Bad", "headers": ["A", "B"], "rows": [{"cells": ["1", "2", "3"]}]}
        ])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)
        assert exc_info.value.status_code == 400
        assert "cell" in exc_info.value.detail.lower()

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_row_too_few_cells_returns_400(self, mock_get_rule, mock_get_pair, db_session, seed_data):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.UUID(seed_data["rule_id"]),
            name="test",
            description="test",
            language_id="1",
            word_category_id="1",
        )
        body = _make_request(seed_data, tables=[
            {"title": "Bad", "headers": ["A", "B", "C"], "rows": [{"cells": ["1"]}]}
        ])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)
        assert exc_info.value.status_code == 400
        assert "cell" in exc_info.value.detail.lower()


class TestValidRequest:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_valid_request_returns_success_with_grammar_rule_id(self, mock_get_rule, mock_get_pair, db_session, seed_data):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.UUID(seed_data["rule_id"]),
            name="test",
            description="test",
            language_id="1",
            word_category_id="1",
        )
        body = _make_request(seed_data)

        result = save_tables(body, db_session)
        assert "grammar_rule_id" in result
        assert result["grammar_rule_id"] == seed_data["rule_id"]
