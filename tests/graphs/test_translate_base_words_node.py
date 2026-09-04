import uuid
from unittest.mock import patch
import pytest
from graphs.nodes.translate_base_words_node import translate_base_words_node
from graphs.models import Translations, TranslationPair


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


def _translations(*pairs):
    return Translations(translations=[TranslationPair(text=t, translation=tr) for t, tr in pairs])


class TestTranslateBaseWordsNode:
    def test_returns_empty_when_no_base_words(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule)
        result = translate_base_words_node(state)
        assert result["base_word_translations"] == {}

    @patch("graphs.nodes.translate_base_words_node.get_language_name_by_id")
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    def test_translates_multiple_words(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.side_effect = ["Spanish", "English"]
        mock_chain.invoke.return_value = _translations(
            ("hablar", "to speak"),
            ("comer", "to eat"),
            ("amigo", "friend"),
        )
        state = _make_state(db_session, grammar_rule, base_words_to_save=[
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablo"]},
            {"text": "comer", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["como"]},
            {"text": "amigo", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["amigo"]},
        ])

        result = translate_base_words_node(state)

        assert result["base_word_translations"] == {
            "hablar": "to speak",
            "comer": "to eat",
            "amigo": "friend",
        }

    @patch("graphs.nodes.translate_base_words_node.get_language_name_by_id")
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    def test_translates_single_word(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.side_effect = ["Spanish", "English"]
        mock_chain.invoke.return_value = _translations(("hablar", "to speak"))
        state = _make_state(db_session, grammar_rule, base_words_to_save=[
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablo"]},
        ])

        result = translate_base_words_node(state)

        assert result["base_word_translations"] == {"hablar": "to speak"}

    @patch("graphs.nodes.translate_base_words_node.get_language_name_by_id")
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    def test_deduplicates_words_before_translating(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.side_effect = ["Spanish", "English"]
        mock_chain.invoke.return_value = _translations(("hablar", "to speak"))
        state = _make_state(db_session, grammar_rule, base_words_to_save=[
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablo"]},
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablas"]},
        ])

        result = translate_base_words_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["items"] == "hablar"
        assert result["base_word_translations"] == {"hablar": "to speak"}

    @patch("graphs.nodes.translate_base_words_node.get_language_name_by_id")
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    def test_passes_language_names_to_chain(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.side_effect = ["Spanish", "English"]
        mock_chain.invoke.return_value = _translations(("hablar", "to speak"))
        state = _make_state(db_session, grammar_rule, base_words_to_save=[
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablo"]},
        ])

        translate_base_words_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["target_language"] == "Spanish"
        assert call_kwargs["native_language"] == "English"

    @patch("graphs.nodes.translate_base_words_node.get_language_name_by_id")
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    def test_preserves_other_state_fields(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.side_effect = ["Spanish", "English"]
        mock_chain.invoke.return_value = _translations(("hablar", "to speak"))
        state = _make_state(db_session, grammar_rule, base_words_to_save=[
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablo"]},
        ])

        result = translate_base_words_node(state)

        assert result["session_id"] == "test-session"
        assert result["word_category_slug"] == "verb"
        assert result["db"] is db_session

    @patch("graphs.nodes.translate_base_words_node.get_language_name_by_id")
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    def test_propagates_llm_errors(self, mock_chain, mock_get_lang, db_session, grammar_rule):
        mock_get_lang.side_effect = ["Spanish", "English"]
        mock_chain.invoke.side_effect = RuntimeError("LLM API error")
        state = _make_state(db_session, grammar_rule, base_words_to_save=[
            {"text": "hablar", "language_id": uuid.uuid4(), "word_category_id": uuid.uuid4(), "forms": ["hablo"]},
        ])

        with pytest.raises(RuntimeError, match="LLM API error"):
            translate_base_words_node(state)
