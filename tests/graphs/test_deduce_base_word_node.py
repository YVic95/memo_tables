import uuid
from unittest.mock import patch
import pytest
from graphs.nodes.deduce_base_word_node import (
    deduce_base_word_node,
    _extract_unique_forms,
    _extract_verb_forms,
    _extract_example_words,
)
from graphs.models import DeducedBaseWords, DeducedBaseWord
from models.word_categories import WordCategory


def _base_words(*entries):
    return DeducedBaseWords(base_words=[DeducedBaseWord(**entry) for entry in entries])


def _verb_base_word(word, word_category_id, *surface_forms):
    return {
        "word": word,
        "word_category_id": word_category_id,
        "surface_forms": list(surface_forms),
    }


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture()
def adjective_category(db_session):
    category = WordCategory(name="Adjectives", slug="adjectives")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _make_state(db_session, grammar_rule, **overrides):
    state = {
        "db": db_session,
        "language_pair_id": uuid.uuid4(),
        "session_id": "test-session",
        "grammar_rule_id": grammar_rule.id,
        "tables": [],
        "target_language_id": uuid.uuid4(),
        "native_language_id": uuid.uuid4(),
        "word_category_slug": "verb",
        "base_words_to_save": [],
        "form_to_base_word_id": {},
    }
    state.update(overrides)
    return state


VERB_TABLE = {
    "title": "Present Tense",
    "headers": ["Pronoun", "Verb", "Example", "Explanation"],
    "rows": [
        {"cells": ["Yo", "hablo", "Yo hablo con mi amigo", "I speak"]},
        {"cells": ["Tú", "hablas", "Tú hablas con mi hermana", "You speak"]},
    ],
}


class TestExtractVerbForms:
    def test_extracts_form_column_only(self):
        result = _extract_verb_forms([VERB_TABLE], {"form": 1})
        assert set(result) == {"hablo", "hablas"}

    def test_deduplicates_across_tables(self):
        tables = [
            {"rows": [{"cells": ["Yo", "hablo", "Yo hablo", "I speak"]}]},
            {"rows": [{"cells": ["Yo", "hablo", "Yo hablo", "I speak"]}]},
        ]
        result = _extract_verb_forms(tables, {"form": 1})
        assert result == ["hablo"]

    def test_strips_whitespace(self):
        tables = [{"rows": [{"cells": ["Yo", "  hablo  ", "Yo hablo", "I speak"]}]}]
        result = _extract_verb_forms(tables, {"form": 1})
        assert result == ["hablo"]

    def test_skips_empty_cells(self):
        tables = [{"rows": [{"cells": ["Yo", "", "", "I speak"]}]}]
        result = _extract_verb_forms(tables, {"form": 1})
        assert result == []

    def test_skips_rows_shorter_than_form_column(self):
        tables = [{"rows": [{"cells": ["Yo", "hablo"]}]}]
        assert _extract_verb_forms(tables, {"form": 1}) == ["hablo"]


class TestExtractExampleWords:
    def test_tokenizes_example_sentences(self):
        result = _extract_example_words([VERB_TABLE], {"example": 2})
        expected = {"yo", "hablo", "con", "mi", "amigo", "tú", "hablas", "hermana"}
        assert set(result) == expected

    def test_strips_punctuation_and_normalizes_case(self):
        tables = [{"rows": [{"cells": ["", "", "¡Hola, Amigo!", ""]}]}]
        result = _extract_example_words(tables, {"example": 2})
        assert set(result) == {"hola", "amigo"}

    def test_returns_empty_when_no_examples(self):
        assert _extract_example_words([], {"example": 2}) == []


class TestExtractUniqueForms:
    def test_extracts_all_cell_values(self):
        tables = [
            {
                "title": "Present Tense",
                "headers": ["Form", "Explanation"],
                "rows": [
                    {"cells": ["hablo", "I speak"]},
                    {"cells": ["hablas", "You speak"]},
                ],
            }
        ]
        result = _extract_unique_forms(tables)
        assert result == ["I speak", "You speak", "hablas", "hablo"]


class TestDeduceBaseWordNode:
    def test_returns_empty_when_no_tables(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, tables=[])
        result = deduce_base_word_node(state)
        assert result["base_words_to_save"] == []

    def test_returns_empty_when_all_cells_empty(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, tables=[
            {"headers": ["Pronoun", "Verb", "Example", "Explanation"], "rows": [{"cells": ["", "", "", ""]}]},
        ])
        result = deduce_base_word_node(state)
        assert result["base_words_to_save"] == []

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_calls_llm_with_surface_forms_and_categories(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category, adjective_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _verb_base_word("hablar", verb_category.id, "hablo", "hablas"),
            _verb_base_word("amigo", adjective_category.id, "amigo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        deduce_base_word_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["target_language"] == "Spanish"
        assert "hablo" in call_kwargs["surface_forms"]
        assert "hablas" in call_kwargs["surface_forms"]
        for token in ("yo", "con", "amigo"):
            assert token in call_kwargs["surface_forms"]
        assert "I speak" not in call_kwargs["surface_forms"]
        assert "Yo" not in call_kwargs["surface_forms"]
        assert str(verb_category.id) in call_kwargs["available_categories"]
        assert str(adjective_category.id) in call_kwargs["available_categories"]
        assert "Nouns (nouns)" in call_kwargs["rule_word_category"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_returns_base_words_with_per_word_categories(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category, adjective_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _verb_base_word("hablar", verb_category.id, "hablo", "hablas"),
            _verb_base_word("amigo", adjective_category.id, "amigo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        result = deduce_base_word_node(state)

        by_text = {item["text"]: item for item in result["base_words_to_save"]}
        assert by_text["hablar"]["word_category_id"] == verb_category.id
        assert by_text["hablar"]["language_id"] == state["target_language_id"]
        assert by_text["hablar"]["forms"] == ["hablo", "hablas"]
        assert by_text["amigo"]["word_category_id"] == adjective_category.id
        assert by_text["amigo"]["forms"] == ["amigo"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_invalid_category_falls_back_to_rule_category(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _verb_base_word("hablar", uuid.uuid4(), "hablo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["word_category_id"] == grammar_rule.word_category_id

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_non_verb_tables_filter_words_to_rule_category(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _verb_base_word("gato", uuid.uuid4(), "gato"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="nouns",
            tables=[
                {"headers": ["Form", "Explanation", "Example"], "rows": [{"cells": ["Masculine", "masculine nouns", "el gato"]}]}
            ],
        )

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["word_category_id"] == grammar_rule.word_category_id

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_preserves_other_state_fields(self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _verb_base_word("hablar", verb_category.id, "hablo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        result = deduce_base_word_node(state)

        assert result["session_id"] == "test-session"
        assert result["word_category_slug"] == "verb"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_propagates_llm_errors(self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.side_effect = RuntimeError("LLM API error")
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        with pytest.raises(RuntimeError, match="LLM API error"):
            deduce_base_word_node(state)

    def test_raises_when_grammar_rule_not_found(self, db_session):
        state = _make_state(
            db_session,
            type("FakeRule", (), {"id": uuid.UUID("00000000-0000-0000-0000-000000000000")})(),
            tables=[VERB_TABLE],
        )
        with pytest.raises(ValueError, match="Grammar rule"):
            deduce_base_word_node(state)