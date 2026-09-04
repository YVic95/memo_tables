import uuid
from sqlalchemy import func
import pytest
from graphs.nodes.save_base_word_node import save_base_word_node
from crud.table_data import get_or_create_base_word
from models.base_words import BaseWord
from models.word_rule_assignments import WordRuleAssignment
from models.word_translations import WordTranslation


def _make_state(db_session, grammar_rule, language_es, language_en, **overrides):
    state = {
        "db": db_session,
        "language_pair_id": uuid.uuid4(),
        "session_id": "test-session",
        "grammar_rule_id": grammar_rule.id,
        "tables": [],
        "target_language_id": language_en.id,
        "native_language_id": language_es.id,
        "word_category_slug": "verb",
        "base_words_to_save": [
            {
                "text": "hablar",
                "language_id": language_en.id,
                "word_category_id": grammar_rule.word_category_id,
                "forms": ["hablo", "hablas"],
            }
        ],
        "base_word_translations": {"hablar": "to speak"},
        "form_to_base_word_id": {},
    }
    state.update(overrides)
    return state


def _count(db_session, model):
    return db_session.query(func.count(model.id)).scalar()


class TestSaveBaseWord:
    def test_creates_base_word_and_assignment(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        result = save_base_word_node(state)

        base_word = db_session.query(BaseWord).filter(BaseWord.text == "hablar").one()
        assert base_word.language_id == language_en.id
        assert base_word.word_category_id == grammar_rule.word_category_id

        assignment = db_session.query(WordRuleAssignment).one()
        assert assignment.base_word_id == base_word.id
        assert assignment.grammar_rule_id == grammar_rule.id

        translation = db_session.query(WordTranslation).one()
        assert translation.base_word_id == base_word.id
        assert translation.language_id == language_es.id
        assert translation.translation == "to speak"

    def test_populates_form_to_base_word_id_map(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        result = save_base_word_node(state)

        base_word = db_session.query(BaseWord).filter(BaseWord.text == "hablar").one()
        assert result["form_to_base_word_id"] == {"hablo": base_word.id, "hablas": base_word.id}

    def test_lowercases_form_map_keys(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(
            db_session, grammar_rule, language_es, language_en,
            base_words_to_save=[
                {"text": "hablar", "language_id": language_en.id,
                 "word_category_id": grammar_rule.word_category_id,
                 "forms": ["Hablo", "hablas"]},
            ],
        )
        result = save_base_word_node(state)

        base_word = db_session.query(BaseWord).filter(BaseWord.text == "hablar").one()
        assert result["form_to_base_word_id"] == {"hablo": base_word.id, "hablas": base_word.id}

    def test_saves_multiple_base_words(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(
            db_session, grammar_rule, language_es, language_en,
            base_words_to_save=[
                {"text": "hablar", "language_id": language_en.id,
                 "word_category_id": grammar_rule.word_category_id,
                 "forms": ["hablo", "hablas"]},
                {"text": "amigo", "language_id": language_en.id,
                 "word_category_id": grammar_rule.word_category_id,
                 "forms": ["amigo"]},
            ],
            base_word_translations={"hablar": "to speak", "amigo": "friend"},
        )
        result = save_base_word_node(state)

        assert _count(db_session, BaseWord) == 2
        assert _count(db_session, WordRuleAssignment) == 2
        assert _count(db_session, WordTranslation) == 2
        amigo = db_session.query(BaseWord).filter(BaseWord.text == "amigo").one()
        assert result["form_to_base_word_id"]["amigo"] == amigo.id

    def test_reuses_existing_base_word(self, db_session, grammar_rule, language_es, language_en):
        existing = get_or_create_base_word(
            db_session, "hablar", language_en.id, grammar_rule.word_category_id
        )
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        result = save_base_word_node(state)

        assert _count(db_session, BaseWord) == 1
        assert result["form_to_base_word_id"]["hablo"] == existing.id

    def test_reuses_existing_translation_and_assignment(self, db_session, grammar_rule, language_es, language_en):
        existing = get_or_create_base_word(
            db_session, "hablar", language_en.id, grammar_rule.word_category_id
        )
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        save_base_word_node(state)
        save_base_word_node(state)

        assert _count(db_session, BaseWord) == 1
        assert _count(db_session, WordRuleAssignment) == 1
        assert _count(db_session, WordTranslation) == 1

    def test_preserves_other_state_fields(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        result = save_base_word_node(state)

        assert result["session_id"] == "test-session"
        assert result["tables"] == state["tables"]

    def test_skips_translation_when_not_in_state(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(db_session, grammar_rule, language_es, language_en,
                           base_word_translations={})
        save_base_word_node(state)

        assert _count(db_session, BaseWord) == 1
        assert _count(db_session, WordTranslation) == 0

    def test_writes_are_rolled_back(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        save_base_word_node(state)

        db_session.rollback()

        assert _count(db_session, BaseWord) == 0
        assert _count(db_session, WordRuleAssignment) == 0
        assert _count(db_session, WordTranslation) == 0

    def test_skips_translation_when_key_missing_from_state(self, db_session, grammar_rule, language_es, language_en):
        state = _make_state(db_session, grammar_rule, language_es, language_en)
        del state["base_word_translations"]
        save_base_word_node(state)

        assert _count(db_session, BaseWord) == 1
        assert _count(db_session, WordTranslation) == 0