import pytest
from crud.table_data import (
    get_or_create_base_word,
    create_word_translation,
    create_word_rule_assignment,
    create_grammar_rule_row,
    create_grammar_rule_row_translation,
    create_word_form,
    create_word_form_translation,
    create_sentence,
    create_sentence_translation,
    create_word_form_sentence,
)


class TestGetOrCreateBaseWord:
    def test_creates_new_base_word(self, db_session, language_es, word_category):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)

        assert word.id is not None
        assert word.text == "gato"
        assert word.language_id == language_es.id
        assert word.word_category_id == word_category.id

    def test_returns_existing_base_word(self, db_session, language_es, word_category):
        first = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        second = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)

        assert first.id == second.id

    def test_different_text_creates_different_word(self, db_session, language_es, word_category):
        word1 = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        word2 = get_or_create_base_word(db_session, "perro", language_es.id, word_category.id)

        assert word1.id != word2.id

    def test_different_language_creates_different_word(self, db_session, language_es, language_en, word_category):
        word1 = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        word2 = get_or_create_base_word(db_session, "gato", language_en.id, word_category.id)

        assert word1.id != word2.id

    def test_different_category_creates_different_word(self, db_session, language_es):
        from models.word_categories import WordCategory
        cat1 = WordCategory(name="Nouns", slug="nouns")
        cat2 = WordCategory(name="Verbs", slug="verbs")
        db_session.add_all([cat1, cat2])
        db_session.commit()
        db_session.refresh(cat1)
        db_session.refresh(cat2)

        word1 = get_or_create_base_word(db_session, "gato", language_es.id, cat1.id)
        word2 = get_or_create_base_word(db_session, "gato", language_es.id, cat2.id)

        assert word1.id != word2.id


class TestCreateWordTranslation:
    def test_creates_translation(self, db_session, language_es, language_en, word_category):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        trans = create_word_translation(db_session, word.id, language_en.id, "cat")

        assert trans.id is not None
        assert trans.base_word_id == word.id
        assert trans.language_id == language_en.id
        assert trans.translation == "cat"


class TestCreateWordRuleAssignment:
    def test_creates_assignment(self, db_session, language_es, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)

        assert assignment.id is not None
        assert assignment.base_word_id == word.id
        assert assignment.grammar_rule_id == grammar_rule.id


class TestCreateGrammarRuleRow:
    def test_creates_row(self, db_session, grammar_rule):
        row = create_grammar_rule_row(
            db_session, grammar_rule.id, "Singular", "Singular form", 1, 0
        )

        assert row.id is not None
        assert row.grammar_rule_id == grammar_rule.id
        assert row.label == "Singular"
        assert row.description == "Singular form"
        assert row.table_no == 1
        assert row.position == 0


class TestCreateGrammarRuleRowTranslation:
    def test_creates_row_translation(self, db_session, grammar_rule, language_en):
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", "Singular form", 1, 0)

        row_trans = create_grammar_rule_row_translation(
            db_session, row.id, language_en.id, "Singular", "Singular form"
        )

        assert row_trans.id is not None
        assert row_trans.grammar_rule_row_id == row.id
        assert row_trans.language_id == language_en.id
        assert row_trans.label_translation == "Singular"
        assert row_trans.description_translation == "Singular form"


class TestCreateWordForm:
    def test_creates_word_form(self, db_session, language_es, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)

        form = create_word_form(db_session, assignment.id, row.id, "gato")

        assert form.id is not None
        assert form.word_rule_assignment_id == assignment.id
        assert form.grammar_rule_row_id == row.id
        assert form.form == "gato"


class TestCreateWordFormTranslation:
    def test_creates_form_translation(self, db_session, language_es, language_en, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)
        form = create_word_form(db_session, assignment.id, row.id, "gato")

        form_trans = create_word_form_translation(db_session, form.id, language_en.id, "cat")

        assert form_trans.id is not None
        assert form_trans.word_form_id == form.id
        assert form_trans.language_id == language_en.id
        assert form_trans.translation == "cat"


class TestCreateSentence:
    def test_creates_sentence(self, db_session, language_es, word_category, grammar_rule):
        sent = create_sentence(
            db_session, "El {gato} duerme", language_es.id, word_category.id, grammar_rule.id, 0
        )

        assert sent.id is not None
        assert sent.template == "El {gato} duerme"
        assert sent.language_id == language_es.id
        assert sent.word_category_id == word_category.id
        assert sent.grammar_rule_id == grammar_rule.id
        assert sent.row_position == 0


class TestCreateSentenceTranslation:
    def test_creates_sentence_translation(self, db_session, language_es, language_en, word_category, grammar_rule):
        sent = create_sentence(
            db_session, "El {gato} duerme", language_es.id, word_category.id, grammar_rule.id, 0
        )
        sent_trans = create_sentence_translation(
            db_session, sent.id, language_en.id, "The {cat} sleeps"
        )

        assert sent_trans.id is not None
        assert sent_trans.sentence_id == sent.id
        assert sent_trans.language_id == language_en.id
        assert sent_trans.template == "The {cat} sleeps"


class TestCreateWordFormSentence:
    def test_creates_word_form_sentence(self, db_session, language_es, language_en, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)
        form = create_word_form(db_session, assignment.id, row.id, "gato")
        sent = create_sentence(
            db_session, "El {gato} duerme", language_es.id, word_category.id, grammar_rule.id, 0
        )

        link = create_word_form_sentence(db_session, form.id, sent.id)

        assert link.id is not None
        assert link.word_form_id == form.id
        assert link.sentence_id == sent.id
