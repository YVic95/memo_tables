import uuid
from unittest.mock import patch
import pytest
from graphs.nodes.deduce_base_word_node import deduce_base_word_node, _extract_unique_forms
from graphs.models import DeducedBaseWords


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
        "base_word_ids": {},
    }
    state.update(overrides)
    return state


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

    def test_deduplicates_across_tables(self):
        tables = [
            {
                "headers": ["Form"],
                "rows": [{"cells": ["hablo"]}],
            },
            {
                "headers": ["Verb"],
                "rows": [{"cells": ["hablo"]}],
            },
        ]
        result = _extract_unique_forms(tables)
        assert result == ["hablo"]

    def test_strips_whitespace(self):
        tables = [
            {
                "headers": ["Form"],
                "rows": [{"cells": ["  hablo  "]}],
            }
        ]
        result = _extract_unique_forms(tables)
        assert result == ["hablo"]

    def test_skips_empty_cells(self):
        tables = [
            {
                "headers": ["Form"],
                "rows": [{"cells": ["hablo", ""]}],
            }
        ]
        result = _extract_unique_forms(tables)
        assert result == ["hablo"]

    def test_returns_empty_list_for_no_tables(self):
        assert _extract_unique_forms([]) == []

    def test_returns_sorted_list(self):
        tables = [{"headers": [], "rows": [{"cells": ["gato", "hablo", "casa"]}]}]
        result = _extract_unique_forms(tables)
        assert result == ["casa", "gato", "hablo"]


class TestDeduceBaseWordNode:
    def test_returns_empty_when_no_tables(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, tables=[])
        result = deduce_base_word_node(state)
        assert result["base_words_to_save"] == []

    def test_returns_empty_when_all_cells_empty(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, tables=[
            {"headers": ["Form"], "rows": [{"cells": [""]}]},
        ])
        result = deduce_base_word_node(state)
        assert result["base_words_to_save"] == []

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_calls_llm_with_correct_params(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = DeducedBaseWords(base_words=["hablar"])
        state = _make_state(db_session, grammar_rule, tables=[
            {
                "headers": ["Form", "Explanation"],
                "rows": [
                    {"cells": ["hablo", "I speak"]},
                    {"cells": ["hablas", "You speak"]},
                ],
            }
        ])
        deduce_base_word_node(state)
        mock_chain.invoke.assert_called_once()
        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["word_category"] == "verb"
        assert call_kwargs["target_language"] == "Spanish"
        assert "hablo" in call_kwargs["inflected_forms"]
        assert "hablas" in call_kwargs["inflected_forms"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_returns_base_words_with_correct_ids(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = DeducedBaseWords(base_words=["hablar", "comer"])
        state = _make_state(db_session, grammar_rule, tables=[
            {"headers": ["Form"], "rows": [{"cells": ["hablo"]}, {"cells": ["como"]}]},
        ])
        result = deduce_base_word_node(state)
        assert len(result["base_words_to_save"]) == 2
        assert result["base_words_to_save"][0]["text"] == "hablar"
        assert result["base_words_to_save"][0]["language_id"] == state["target_language_id"]
        assert result["base_words_to_save"][0]["word_category_id"] == grammar_rule.word_category_id

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_preserves_other_state_fields(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = DeducedBaseWords(base_words=["hablar"])
        state = _make_state(db_session, grammar_rule, tables=[
            {"headers": ["Form"], "rows": [{"cells": ["hablo"]}]},
        ])
        result = deduce_base_word_node(state)
        assert result["session_id"] == "test-session"
        assert result["word_category_slug"] == "verb"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_propagates_llm_errors(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.side_effect = RuntimeError("LLM API error")
        state = _make_state(db_session, grammar_rule, tables=[
            {"headers": ["Form"], "rows": [{"cells": ["hablo"]}]},
        ])
        with pytest.raises(RuntimeError, match="LLM API error"):
            deduce_base_word_node(state)

    def test_raises_when_grammar_rule_not_found(self, db_session):
        state = _make_state(
            db_session,
            type("FakeRule", (), {"id": uuid.UUID("00000000-0000-0000-0000-000000000000")})(),
            tables=[{"headers": ["Form"], "rows": [{"cells": ["hablo"]}]}],
        )
        with pytest.raises(ValueError, match="Grammar rule"):
            deduce_base_word_node(state)
