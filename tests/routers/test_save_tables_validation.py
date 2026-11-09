import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base
from models.language import Language
from models.language_pairs import LanguagePair
from models.word_categories import WordCategory
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from graphs.models import SaveTablesRequest
from tests.graphs.generation_helpers import (
    ADJ_GENDER_TABLE,
    ADJ_NUMBER_HEADERS,
    ADJ_NUMBER_TABLE,
    ADJ_OTHER_TABLE,
    NOUN_NUMBER_HEADERS,
    NOUN_NUMBER_TABLE,
)
from routers.save_tables_agent import save_tables


@pytest.fixture(autouse=True)
def mock_graph(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("routers.save_tables_agent.graph", mock)
    return mock


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

    cat = WordCategory(name="Nouns", slug="noun")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    canon = CanonicalRule(
        native_language_id=lang_en.id,
        target_language_id=lang_es.id,
        word_category_id=cat.id,
        level="A1",
        name="Noun Gender",
        description="Masculine vs feminine",
        position=1,
        slug="noun-gender",
        is_active=True,
    )
    db_session.add(canon)
    db_session.commit()
    db_session.refresh(canon)

    rule = GrammarRule(
        name="Noun Gender",
        description="Masculine vs feminine",
        language_id=lang_es.id,
        word_category_id=cat.id,
        canonical_rule_id=canon.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    return {
        "pair_id": pair.pair_id,
        "rule_id": rule.id,
    }


def _noun_table(title="Noun Gender", **overrides):
    table = NOUN_NUMBER_TABLE.model_dump()
    table["title"] = title
    table.update(overrides)
    return table


def _make_request(seed_data, **overrides):
    defaults = {
        "language_pair_id": seed_data["pair_id"],
        "session_id": uuid.uuid4(),
        "grammar_rule_id": seed_data["rule_id"],
        "tables": [_noun_table()],
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
            id=seed_data["rule_id"],
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
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
            id=seed_data["rule_id"],
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
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
            id=seed_data["rule_id"],
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
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
            id=seed_data["rule_id"],
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
        )
        body = _make_request(seed_data, tables=[
            {"title": "Bad", "headers": ["A", "B", "C"], "rows": [{"cells": ["1"]}]}
        ])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)
        assert exc_info.value.status_code == 400
        assert "cell" in exc_info.value.detail.lower()


class TestValidRequest:
    @patch("routers.save_tables_agent.build_markdown_tables")
    @patch("routers.save_tables_agent.get_table_data")
    @patch("routers.save_tables_agent.get_word_category_by_id")
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_valid_request_returns_success_with_grammar_rule_id(
        self, mock_get_rule, mock_get_pair, mock_get_category, mock_get_table_data, mock_build_md,
        db_session, seed_data,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"],
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
        )
        mock_get_category.return_value = WordCategory(name="Nouns", slug="noun")
        mock_get_table_data.return_value = []
        mock_build_md.return_value = {"noun": ""}
        body = _make_request(seed_data)

        result = save_tables(body, db_session)
        assert result["status"] == "saved"
        assert result["grammar_rule_id"] == str(seed_data["rule_id"])
        assert result["message"] == (
            "Saved 1 table: 'Noun Gender' (2 rows). "
            "Stored 0 sentences, 0 word forms, 0 base words."
        )
        assert "skeleton_table" in result


class TestGraphInvocation:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_valid_request_invokes_graph_and_commits(
        self, mock_count_saved_data, mock_get_rule, mock_get_pair, seed_data, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"],
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
        )
        mock_count_saved_data.return_value = {"sentences": 3, "word_forms": 5, "base_words": 1}
        mock_db = MagicMock()
        body = _make_request(seed_data)

        result = save_tables(body, mock_db)

        assert result["status"] == "saved"
        assert result["grammar_rule_id"] == str(seed_data["rule_id"])
        assert result["message"] == (
            "Saved 1 table: 'Noun Gender' (2 rows). "
            "Stored 3 sentences, 5 word forms, 1 base word."
        )
        mock_count_saved_data.assert_called_once_with(mock_db, seed_data["rule_id"])
        state = mock_graph.invoke.call_args.args[0]
        assert state["db"] is mock_db
        assert state["language_pair_id"] == body.language_pair_id
        assert state["session_id"] == str(body.session_id)
        assert state["grammar_rule_id"] == body.grammar_rule_id
        assert state["tables"] == [t.model_dump() for t in body.tables]
        assert state["target_language_id"] is None
        assert state["native_language_id"] is None
        assert state["word_category_slug"] is None
        assert state["base_words_to_save"] == []
        assert state["form_to_base_word_id"] == {}
        mock_db.commit.assert_called_once()

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_message_lists_each_table_with_its_row_count(
        self, mock_count_saved_data, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(),
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
        )
        mock_count_saved_data.return_value = {"sentences": 1, "word_forms": 2, "base_words": 1}
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[
                {"title": "Presente", "headers": ["A"], "rows": [{"cells": ["x"]}, {"cells": ["y"]}]},
                {"title": "Género", "headers": ["A"], "rows": [{"cells": ["z"]}]},
            ],
        )

        result = save_tables(body, MagicMock())

        assert result["message"] == (
            "Saved 2 tables: 'Presente' (2 rows), 'Género' (1 row). "
            "Stored 1 sentence, 2 word forms, 1 base word."
        )

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_rolls_back_and_reraises_when_graph_fails(
        self, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(),
            name="test",
            description="test",
            language_id="1",
            word_category_id=str(uuid.uuid4()),
        )
        mock_graph.invoke.side_effect = RuntimeError("boom")
        mock_db = MagicMock()
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[{"title": "T", "headers": ["A"], "rows": [{"cells": ["x"]}]}],
        )

        with pytest.raises(RuntimeError, match="boom"):
            save_tables(body, mock_db)

        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()


class TestTableFiltering:
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_fragmented_tables_only_when_both_exist(
        self, mock_count_saved_data, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(), name="t", description="t",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_count_saved_data.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[
                {"title": "General", "headers": ["A"], "rows": [{"cells": ["x"]}]},
                {"title": "Frag 1", "headers": ["A"], "rows": [{"cells": ["a"]}], "fragmented_table_id": 1},
                {"title": "Frag 2", "headers": ["A"], "rows": [{"cells": ["b"]}], "fragmented_table_id": 2},
            ],
        )

        result = save_tables(body, MagicMock())

        state = mock_graph.invoke.call_args.args[0]
        saved_titles = [t["title"] for t in state["tables"]]
        assert saved_titles == ["Frag 1", "Frag 2"]
        assert "General" not in saved_titles
        assert "Saved 2 tables" in result["message"]

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_general_table_used_when_no_fragmented(
        self, mock_count_saved_data, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(), name="t", description="t",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_count_saved_data.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[
                {"title": "General", "headers": ["A"], "rows": [{"cells": ["x"]}]},
            ],
        )

        result = save_tables(body, MagicMock())

        state = mock_graph.invoke.call_args.args[0]
        saved_titles = [t["title"] for t in state["tables"]]
        assert saved_titles == ["General"]
        assert "Saved 1 table" in result["message"]

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_empty_fragmented_falls_back_to_general(
        self, mock_count_saved_data, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(), name="t", description="t",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_count_saved_data.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[
                {"title": "General", "headers": ["A"], "rows": [{"cells": ["x"]}]},
            ],
        )
        body.tables[0].fragmented_table_id = None

        result = save_tables(body, MagicMock())

        state = mock_graph.invoke.call_args.args[0]
        saved_titles = [t["title"] for t in state["tables"]]
        assert saved_titles == ["General"]

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    def test_bad_general_table_skipped_when_fragmented_exist(
        self, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(), name="t", description="t",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[
                {"title": "Bad General", "headers": ["A", "B"], "rows": [{"cells": ["only one"]}]},
                {"title": "Good Frag", "headers": ["A"], "rows": [{"cells": ["ok"]}], "fragmented_table_id": 1},
            ],
        )

        result = save_tables(body, MagicMock())

        state = mock_graph.invoke.call_args.args[0]
        saved_titles = [t["title"] for t in state["tables"]]
        assert saved_titles == ["Good Frag"]

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_message_describes_only_saved_tables(
        self, mock_count_saved_data, mock_get_rule, mock_get_pair, mock_graph
    ):
        mock_get_pair.return_value = {"pair_id": uuid.uuid4()}
        mock_get_rule.return_value = GrammarRule(
            id=uuid.uuid4(), name="t", description="t",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_count_saved_data.return_value = {"sentences": 1, "word_forms": 2, "base_words": 1}
        body = SaveTablesRequest(
            language_pair_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            grammar_rule_id=uuid.uuid4(),
            tables=[
                {"title": "General", "headers": ["A"], "rows": [{"cells": ["x"]}, {"cells": ["y"]}]},
                {"title": "Frag 1", "headers": ["A"], "rows": [{"cells": ["a"]}], "fragmented_table_id": 1},
            ],
        )

        result = save_tables(body, MagicMock())

        assert "General" not in result["message"]
        assert "Frag 1" in result["message"]
        assert "Saved 1 table" in result["message"]


class TestSkeletonTable:
    @patch("routers.save_tables_agent.build_markdown_tables")
    @patch("routers.save_tables_agent.get_table_data")
    @patch("routers.save_tables_agent.get_word_category_by_id")
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_response_includes_skeleton_table_field(
        self, mock_count, mock_get_rule, mock_get_pair,
        mock_get_category, mock_get_table_data, mock_build_md,
        seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="test", description="test",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_get_category.return_value = WordCategory(name="Verbs", slug="verbs")
        mock_count.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        mock_get_table_data.return_value = [
            {"table_no": 1, "entries": [{"label": "1st", "base_word_text": "hablar", "form": "hablo"}]}
        ]
        mock_build_md.return_value = {"verbs": "| Label | Verb: hablar |\n| --- | --- |\n| 1st | hablo |"}
        body = _make_request(seed_data)

        result = save_tables(body, db_session)

        assert "skeleton_table" in result
        assert isinstance(result["skeleton_table"], dict)

    @patch("routers.save_tables_agent.build_markdown_tables")
    @patch("routers.save_tables_agent.get_table_data")
    @patch("routers.save_tables_agent.get_word_category_by_id")
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_skeleton_table_keyed_by_category_slug(
        self, mock_count, mock_get_rule, mock_get_pair,
        mock_get_category, mock_get_table_data, mock_build_md,
        seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="test", description="test",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_get_category.return_value = WordCategory(name="Verbs", slug="verbs")
        mock_count.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        mock_get_table_data.return_value = [
            {"table_no": 1, "entries": [{"label": "1st", "base_word_text": "hablar", "form": "hablo"}]}
        ]
        mock_build_md.return_value = {"verbs": "| 1st | hablo |"}
        body = _make_request(seed_data)

        result = save_tables(body, db_session)

        assert "verbs" in result["skeleton_table"]
        assert result["skeleton_table"]["verbs"] == "| 1st | hablo |"

    @patch("routers.save_tables_agent.build_markdown_tables")
    @patch("routers.save_tables_agent.get_table_data")
    @patch("routers.save_tables_agent.get_word_category_by_id")
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_does_not_break_existing_response_fields(
        self, mock_count, mock_get_rule, mock_get_pair,
        mock_get_category, mock_get_table_data, mock_build_md,
        seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="test", description="test",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_get_category.return_value = WordCategory(name="Nouns", slug="noun")
        mock_count.return_value = {"sentences": 1, "word_forms": 2, "base_words": 1}
        mock_get_table_data.return_value = []
        mock_build_md.return_value = {"noun": ""}
        body = _make_request(seed_data)

        result = save_tables(body, db_session)

        assert result["status"] == "saved"
        assert result["grammar_rule_id"] == str(seed_data["rule_id"])
        assert "sentence" in result["message"]
        assert "skeleton_table" in result

    @patch("routers.save_tables_agent.build_markdown_tables")
    @patch("routers.save_tables_agent.get_table_data")
    @patch("routers.save_tables_agent.get_word_category_by_id")
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_response_includes_rule_title(
        self, mock_count, mock_get_rule, mock_get_pair,
        mock_get_category, mock_get_table_data, mock_build_md,
        seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="Plural Agreement", description="test",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_get_category.return_value = WordCategory(name="Nouns", slug="noun")
        mock_count.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        mock_get_table_data.return_value = []
        mock_build_md.return_value = {"noun": ""}
        body = _make_request(seed_data)

        result = save_tables(body, db_session)

        assert result["rule_title"] == "Plural Agreement"

    @patch("routers.save_tables_agent.build_noun_skeleton_tables")
    @patch("routers.save_tables_agent.get_word_category_by_id")
    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_noun_skeleton_uses_merged_table_title(
        self, mock_count, mock_get_rule, mock_get_pair, mock_get_category,
        mock_build_noun_skeleton, seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="Plural Agreement", description="test",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_get_category.return_value = WordCategory(name="Nouns", slug="noun")
        mock_count.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        mock_build_noun_skeleton.return_value = {"noun": "| Singular | Plural |"}
        body = _make_request(seed_data, tables=[
            {
                "title": "Nouns — Singular",
                "headers": ["Singular", "Traducción", "Explicación", "Ejemplo"],
                "rows": [{"cells": ["el gato", "the cat", "Masculine", "El gato duerme."]}],
                "fragmented_table_id": 1,
                "noun_table_layout": "noun_number",
            },
            {
                "title": "Nouns — Plural",
                "headers": ["Plural", "Traducción", "Explicación", "Ejemplo"],
                "rows": [{"cells": ["los gatos", "the cats", "Plural", "Los gatos duermen."]}],
                "fragmented_table_id": 2,
                "noun_table_layout": "noun_number",
            },
        ])

        result = save_tables(body, db_session)

        assert result["skeleton_titles"] == {"noun": ["Nouns"]}
        assert result["skeleton_table"] == {"noun": "| Singular | Plural |"}
        mock_build_noun_skeleton.assert_called_once_with(
            db_session, seed_data["rule_id"], "noun_number"
        )

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_skeleton_table_not_called_on_graph_failure(
        self, mock_count, mock_get_rule, mock_get_pair, seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="test", description="test",
            language_id="1", word_category_id=str(uuid.uuid4()),
        )
        mock_graph.invoke.side_effect = RuntimeError("boom")
        body = _make_request(seed_data)

        with pytest.raises(RuntimeError, match="boom"):
            save_tables(body, db_session)


class TestNounTableValidation:
    def test_missing_noun_layout_returns_400(self, seed_data, mock_graph, db_session):
        table = _noun_table()
        table.pop("noun_table_layout")
        body = _make_request(seed_data, tables=[table])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "layout" in exc_info.value.detail.lower()
        assert "regenerate" in exc_info.value.detail.lower()
        mock_graph.invoke.assert_not_called()

    def test_noun_table_with_wrong_column_count_returns_400(
        self, seed_data, mock_graph, db_session
    ):
        table = {
            "title": "Half Table",
            "headers": NOUN_NUMBER_HEADERS[:4],
            "rows": [
                {"cells": ["el gato", "the cat", "Masculine", "El gato duerme."]}
            ],
            "noun_table_layout": "noun_number",
        }
        body = _make_request(seed_data, tables=[table])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "8 columns" in exc_info.value.detail
        assert "regenerate" in exc_info.value.detail.lower()
        mock_graph.invoke.assert_not_called()

    def test_valid_eight_column_noun_table_is_saved(
        self, seed_data, mock_graph, db_session
    ):
        body = _make_request(seed_data)

        result = save_tables(body, db_session)

        assert result["status"] == "saved"
        mock_graph.invoke.assert_called_once()


class TestNounFragmentMerge:
    def test_two_side_fragments_merge_into_one_eight_column_table(
        self, seed_data, mock_graph, db_session
    ):
        body = _make_request(seed_data, tables=[
            {
                "title": "Nouns — Singular",
                "headers": ["Singular", "Traducción", "Explicación", "Ejemplo"],
                "rows": [
                    {
                        "cells": ["el gato", "the cat", "Masculine", "El gato duerme."],
                        "row_position": 0,
                    },
                    {
                        "cells": ["la mesa", "the table", "Feminine", "La mesa es grande."],
                        "row_position": 1,
                    },
                ],
                "fragmented_table_id": 1,
                "noun_table_layout": "noun_number",
            },
            {
                "title": "Nouns — Plural",
                "headers": ["Plural", "Traducción", "Explicación", "Ejemplo"],
                "rows": [
                    {
                        "cells": ["los gatos", "the cats", "Plural", "Los gatos duermen."],
                        "row_position": 0,
                    },
                    {
                        "cells": ["las mesas", "the tables", "Plural", "Las mesas son grandes."],
                        "row_position": 1,
                    },
                ],
                "fragmented_table_id": 2,
                "noun_table_layout": "noun_number",
            },
        ])

        result = save_tables(body, db_session)

        state = mock_graph.invoke.call_args.args[0]
        assert len(state["tables"]) == 1
        merged = state["tables"][0]
        assert merged["title"] == "Nouns"
        assert merged["headers"] == NOUN_NUMBER_HEADERS
        assert merged["noun_table_layout"] == "noun_number"
        assert merged["rows"][0]["cells"] == [
            "el gato",
            "the cat",
            "Masculine",
            "El gato duerme.",
            "los gatos",
            "the cats",
            "Plural",
            "Los gatos duermen.",
        ]
        assert merged["rows"][1]["cells"] == [
            "la mesa",
            "the table",
            "Feminine",
            "La mesa es grande.",
            "las mesas",
            "the tables",
            "Plural",
            "Las mesas son grandes.",
        ]
        assert "Saved 1 table" in result["message"]

    def test_mismatched_fragment_row_counts_returns_400(
        self, seed_data, mock_graph, db_session
    ):
        body = _make_request(seed_data, tables=[
            {
                "title": "Nouns — Singular",
                "headers": ["Singular", "Traducción", "Explicación", "Ejemplo"],
                "rows": [
                    {"cells": ["el gato", "the cat", "Masculine", "El gato duerme."]}
                ],
                "fragmented_table_id": 1,
                "noun_table_layout": "noun_number",
            },
            {
                "title": "Nouns — Plural",
                "headers": ["Plural", "Traducción", "Explicación", "Ejemplo"],
                "rows": [],
                "fragmented_table_id": 2,
                "noun_table_layout": "noun_number",
            },
        ])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "same number of pairs" in exc_info.value.detail.lower()
        mock_graph.invoke.assert_not_called()


@pytest.fixture()
def adjective_seed_data(db_session):
    lang_es = Language(code="es", name="Spanish")
    lang_en = Language(code="en", name="English")
    db_session.add_all([lang_es, lang_en])
    db_session.commit()
    db_session.refresh(lang_es)
    db_session.refresh(lang_en)

    pair = LanguagePair(
        native_language_id=lang_en.id,
        target_language_id=lang_es.id,
    )
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)

    cat = WordCategory(name="Adjectives", slug="adjective")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    canon = CanonicalRule(
        native_language_id=lang_en.id,
        target_language_id=lang_es.id,
        word_category_id=cat.id,
        level="A1",
        name="Adjective Agreement",
        description="Adjectives agree",
        position=1,
        slug="adj-agreement",
        is_active=True,
    )
    db_session.add(canon)
    db_session.commit()
    db_session.refresh(canon)

    rule = GrammarRule(
        name="Adjective Agreement",
        description="Adjectives agree",
        language_id=lang_es.id,
        word_category_id=cat.id,
        canonical_rule_id=canon.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    return {
        "pair_id": pair.pair_id,
        "rule_id": rule.id,
    }


def _adj_request(seed_data, tables):
    return SaveTablesRequest(
        language_pair_id=seed_data["pair_id"],
        session_id=uuid.uuid4(),
        grammar_rule_id=seed_data["rule_id"],
        tables=tables,
    )


def _adj_side_fragment(base, side, fragment_id):
    headers = base["headers"][:4] if side == 0 else base["headers"][4:]
    return {
        "title": f"{base['title']} — {headers[0]}",
        "headers": headers,
        "rows": [
            {"cells": row["cells"][:4] if side == 0 else row["cells"][4:], "row_position": i}
            for i, row in enumerate(base["rows"])
        ],
        "fragmented_table_id": fragment_id,
        "adjective_table_layout": base["adjective_table_layout"],
    }


class TestAdjectiveSaveTables:
    def test_unified_fragments_merge_into_two_pair_tables(
        self, mock_graph, db_session, adjective_seed_data
    ):
        number = ADJ_NUMBER_TABLE.model_dump()
        gender = ADJ_GENDER_TABLE.model_dump()
        body = _adj_request(adjective_seed_data, tables=[
            number,
            gender,
            _adj_side_fragment(number, 0, 1),
            _adj_side_fragment(number, 1, 2),
            _adj_side_fragment(gender, 0, 3),
            _adj_side_fragment(gender, 1, 4),
        ])

        result = save_tables(body, db_session)

        state = mock_graph.invoke.call_args.args[0]
        assert len(state["tables"]) == 2
        merged_number, merged_gender = state["tables"]
        assert merged_number["title"] == ADJ_NUMBER_TABLE.title
        assert merged_gender["title"] == ADJ_GENDER_TABLE.title
        assert merged_number["adjective_table_layout"] == "adj_number_gender"
        assert [row["cells"] for row in merged_number["rows"]] == [
            row.cells for row in ADJ_NUMBER_TABLE.rows
        ]
        assert [row["cells"] for row in merged_gender["rows"]] == [
            row.cells for row in ADJ_GENDER_TABLE.rows
        ]
        assert "Saved 2 tables" in result["message"]

    def test_other_table_passes_through_unsplit(
        self, mock_graph, db_session, adjective_seed_data
    ):
        body = _adj_request(
            adjective_seed_data, tables=[ADJ_OTHER_TABLE.model_dump()]
        )

        result = save_tables(body, db_session)

        state = mock_graph.invoke.call_args.args[0]
        assert len(state["tables"]) == 1
        assert state["tables"][0]["headers"] == ADJ_OTHER_TABLE.headers
        assert "Saved 1 table" in result["message"]

    def test_other_table_with_wrong_column_count_returns_400(
        self, mock_graph, db_session, adjective_seed_data
    ):
        table = ADJ_OTHER_TABLE.model_dump()
        table["headers"] = table["headers"] + ["Extra"]
        body = _adj_request(adjective_seed_data, tables=[table])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "4 columns" in exc_info.value.detail
        mock_graph.invoke.assert_not_called()

    def test_pair_table_with_wrong_column_count_returns_400(
        self, mock_graph, db_session, adjective_seed_data
    ):
        table = ADJ_NUMBER_TABLE.model_dump()
        table["headers"] = table["headers"][:7]
        body = _adj_request(adjective_seed_data, tables=[table])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "8 columns" in exc_info.value.detail
        mock_graph.invoke.assert_not_called()

    def test_missing_layout_with_unreadable_shape_returns_400(
        self, mock_graph, db_session, adjective_seed_data
    ):
        table = ADJ_NUMBER_TABLE.model_dump()
        table["adjective_table_layout"] = None
        table["headers"] = table["headers"][:3]
        table["rows"] = [{"cells": row["cells"][:3]} for row in table["rows"]]
        body = _adj_request(adjective_seed_data, tables=[table])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "regenerate" in exc_info.value.detail.lower()
        mock_graph.invoke.assert_not_called()

    def test_mismatched_fragment_row_counts_returns_400(
        self, mock_graph, db_session, adjective_seed_data
    ):
        number = ADJ_NUMBER_TABLE.model_dump()
        fragments = [
            _adj_side_fragment(number, 0, 1),
            {**_adj_side_fragment(number, 1, 2), "rows": []},
        ]
        body = _adj_request(adjective_seed_data, tables=[number, *fragments])

        with pytest.raises(HTTPException) as exc_info:
            save_tables(body, db_session)

        assert exc_info.value.status_code == 400
        assert "same number of pairs" in exc_info.value.detail.lower()
        mock_graph.invoke.assert_not_called()

    @patch("routers.save_tables_agent.build_adjective_skeleton_tables")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_other_skeleton_uses_single_form_column(
        self, mock_count, mock_build_skeleton, mock_graph, db_session, adjective_seed_data
    ):
        mock_count.return_value = {"sentences": 0, "word_forms": 0, "base_words": 0}
        mock_build_skeleton.return_value = {"adjective": "| Adjetivo |"}
        body = _adj_request(
            adjective_seed_data, tables=[ADJ_OTHER_TABLE.model_dump()]
        )

        result = save_tables(body, db_session)

        mock_build_skeleton.assert_called_once_with(
            db_session, adjective_seed_data["rule_id"], {0: ("Adjetivo",)}
        )
        assert result["skeleton_titles"] == {"adjective": ["Los demostrativos"]}
        assert result["skeleton_table"] == {"adjective": "| Adjetivo |"}
