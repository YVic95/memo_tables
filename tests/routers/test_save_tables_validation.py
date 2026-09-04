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
from models.grammar_rules import GrammarRule
from graphs.models import SaveTablesRequest
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
        "pair_id": pair.pair_id,
        "rule_id": rule.id,
    }


def _make_request(seed_data, **overrides):
    defaults = {
        "language_pair_id": seed_data["pair_id"],
        "session_id": uuid.uuid4(),
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
            id=seed_data["rule_id"],
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
            id=seed_data["rule_id"],
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
            id=seed_data["rule_id"],
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
            id=seed_data["rule_id"],
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
            word_category_id="1",
        )
        mock_get_category.return_value = WordCategory(name="Nouns", slug="nouns")
        mock_get_table_data.return_value = []
        mock_build_md.return_value = {"nouns": ""}
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
            word_category_id="1",
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
            word_category_id="1",
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
            word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
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
            language_id="1", word_category_id="1",
        )
        mock_get_category.return_value = WordCategory(name="Nouns", slug="nouns")
        mock_count.return_value = {"sentences": 1, "word_forms": 2, "base_words": 1}
        mock_get_table_data.return_value = []
        mock_build_md.return_value = {"nouns": ""}
        body = _make_request(seed_data)

        result = save_tables(body, db_session)

        assert result["status"] == "saved"
        assert result["grammar_rule_id"] == str(seed_data["rule_id"])
        assert "sentence" in result["message"]
        assert "skeleton_table" in result

    @patch("routers.save_tables_agent.get_language_pair_by_id")
    @patch("routers.save_tables_agent.get_grammar_rule_by_id")
    @patch("routers.save_tables_agent.count_saved_data")
    def test_skeleton_table_not_called_on_graph_failure(
        self, mock_count, mock_get_rule, mock_get_pair, seed_data, mock_graph, db_session,
    ):
        mock_get_pair.return_value = {"pair_id": seed_data["pair_id"]}
        mock_get_rule.return_value = GrammarRule(
            id=seed_data["rule_id"], name="test", description="test",
            language_id="1", word_category_id="1",
        )
        mock_graph.invoke.side_effect = RuntimeError("boom")
        body = _make_request(seed_data)

        with pytest.raises(RuntimeError, match="boom"):
            save_tables(body, db_session)
