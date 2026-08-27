import uuid
import pytest
from graphs.nodes.fetch_context_node import fetch_context_node
from models.language_pairs import LanguagePair


@pytest.fixture()
def language_pair(db_session, language_es, language_en):
    pair = LanguagePair(
        native_language_id=language_es.id,
        target_language_id=language_en.id,
    )
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)
    return pair


def _make_state(db_session, grammar_rule, pair, **overrides):
    state = {
        "db": db_session,
        "language_pair_id": pair.pair_id,
        "session_id": "test-session",
        "grammar_rule_id": grammar_rule.id,
        "tables": [],
        "target_language_id": "",
        "native_language_id": "",
        "word_category_slug": "",
        "base_words_to_save": [],
        "base_word_ids": {},
    }
    state.update(overrides)
    return state


class TestFetchContextPopulatesState:
    def test_populates_word_category_slug(self, db_session, grammar_rule, word_category, language_pair):
        state = _make_state(db_session, grammar_rule, language_pair)
        result = fetch_context_node(state)
        assert result["word_category_slug"] == word_category.slug

    def test_populates_target_language_id(self, db_session, grammar_rule, language_en, language_pair):
        state = _make_state(db_session, grammar_rule, language_pair)
        result = fetch_context_node(state)
        assert result["target_language_id"] == language_en.id

    def test_populates_native_language_id(self, db_session, grammar_rule, language_es, language_pair):
        state = _make_state(db_session, grammar_rule, language_pair)
        result = fetch_context_node(state)
        assert result["native_language_id"] == language_es.id

    def test_preserves_existing_state_fields(self, db_session, grammar_rule, language_pair):
        state = _make_state(db_session, grammar_rule, language_pair,
            tables=[{"title": "test"}],
            base_words_to_save=[{"text": "gato"}],
            base_word_ids={"gato": "some-id"},
        )
        result = fetch_context_node(state)
        assert result["session_id"] == "test-session"
        assert result["tables"] == [{"title": "test"}]
        assert result["base_words_to_save"] == [{"text": "gato"}]
        assert result["base_word_ids"] == {"gato": "some-id"}


class TestFetchContextMissingRule:
    def test_raises_error_when_rule_not_found(self, db_session, language_es, language_en, language_pair):
        state = _make_state(db_session, type("FakeRule", (), {"id": uuid.UUID("00000000-0000-0000-0000-000000000000")})(), language_pair)
        with pytest.raises(ValueError, match="Grammar rule"):
            fetch_context_node(state)

    def test_raises_error_when_language_pair_not_found(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, type("FakePair", (), {"pair_id": uuid.UUID("00000000-0000-0000-0000-000000000000")})())
        with pytest.raises(ValueError, match="Language pair"):
            fetch_context_node(state)
