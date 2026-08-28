import pytest
from crud.table_data import (
    get_or_create_base_word,
    get_or_create_word_translation,
    get_or_create_word_rule_assignment,
    get_or_create_word_form,
    get_or_create_word_form_translation,
    count_saved_data,
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
from models.grammar_rules import GrammarRule
from models.base_words import BaseWord
from models.word_translations import WordTranslation
from models.word_rule_assignments import WordRuleAssignment
from models.grammar_rule_rows import GrammarRuleRow
from models.grammar_rule_row_translations import GrammarRuleRowTranslation
from models.word_forms import WordForm
from models.word_form_translations import WordFormTranslation
from models.sentences import Sentence
from models.sentence_translations import SentenceTranslation
from models.word_form_sentences import WordFormSentence


def _row_count(db_session, model):
    from sqlalchemy import func
    return db_session.query(func.count(model.id)).scalar()


class TestCommitFalseBehavior:
    def test_commit_false_writes_are_visible_in_session(self, db_session, language_es, word_category):
        word = get_or_create_base_word(
            db_session, "gato", language_es.id, word_category.id, commit=False
        )

        assert word.id is not None
        assert _row_count(db_session, BaseWord) == 1

    def test_commit_false_rolls_back_writes(self, db_session, language_es, word_category):
        get_or_create_base_word(db_session, "gato", language_es.id, word_category.id, commit=False)

        db_session.rollback()

        assert _row_count(db_session, BaseWord) == 0

    def test_commit_true_persists_through_rollback(self, db_session, language_es, word_category):
        get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)

        db_session.rollback()

        assert _row_count(db_session, BaseWord) == 1

    def test_commit_false_deduplicates_pending_base_word(self, db_session, language_es, word_category):
        first = get_or_create_base_word(
            db_session, "gato", language_es.id, word_category.id, commit=False
        )
        second = get_or_create_base_word(
            db_session, "gato", language_es.id, word_category.id, commit=False
        )

        assert first.id == second.id
        assert _row_count(db_session, BaseWord) == 1

    def test_commit_false_applies_to_all_write_functions(
        self, db_session, language_es, language_en, word_category, grammar_rule
    ):
        word = get_or_create_base_word(
            db_session, "gato", language_es.id, word_category.id, commit=False
        )
        create_word_translation(db_session, word.id, language_en.id, "cat", commit=False)
        create_word_rule_assignment(db_session, word.id, grammar_rule.id, commit=False)
        row = create_grammar_rule_row(
            db_session, grammar_rule.id, "Singular", None, 1, 0, commit=False
        )
        create_grammar_rule_row_translation(
            db_session, row.id, language_en.id, "Singular", None, commit=False
        )
        assignment = db_session.query(WordRuleAssignment).first()
        form = create_word_form(
            db_session, assignment.id, row.id, "gato", commit=False
        )
        create_word_form_translation(db_session, form.id, language_en.id, "cat", commit=False)
        sentence = create_sentence(
            db_session, "El gato duerme", language_es.id, word_category.id, grammar_rule.id, 0,
            commit=False,
        )
        create_sentence_translation(
            db_session, sentence.id, language_en.id, "The cat sleeps", commit=False
        )
        create_word_form_sentence(db_session, form.id, sentence.id, commit=False)

        db_session.rollback()

        assert _row_count(db_session, BaseWord) == 0
        assert _row_count(db_session, WordTranslation) == 0
        assert _row_count(db_session, WordRuleAssignment) == 0
        assert _row_count(db_session, GrammarRuleRow) == 0
        assert _row_count(db_session, GrammarRuleRowTranslation) == 0
        assert _row_count(db_session, WordForm) == 0
        assert _row_count(db_session, WordFormTranslation) == 0
        assert _row_count(db_session, Sentence) == 0
        assert _row_count(db_session, SentenceTranslation) == 0
        assert _row_count(db_session, WordFormSentence) == 0


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


class TestGetOrCreateWordTranslation:
    def test_returns_existing_translation_for_pair(self, db_session, language_es, language_en, word_category):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        first = get_or_create_word_translation(db_session, word.id, language_en.id, "cat")
        second = get_or_create_word_translation(db_session, word.id, language_en.id, "cat")

        assert first.id == second.id
        assert db_session.query(WordTranslation).count() == 1

    def test_different_language_creates_different_translation(self, db_session, language_es, language_en, word_category):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        get_or_create_word_translation(db_session, word.id, language_en.id, "cat")
        get_or_create_word_translation(db_session, word.id, language_es.id, "gato")

        assert db_session.query(WordTranslation).count() == 2


class TestCreateWordRuleAssignment:
    def test_creates_assignment(self, db_session, language_es, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)

        assert assignment.id is not None
        assert assignment.base_word_id == word.id
        assert assignment.grammar_rule_id == grammar_rule.id


class TestGetOrCreateWordRuleAssignment:
    def test_returns_existing_assignment_for_pair(self, db_session, language_es, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        first = get_or_create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        second = get_or_create_word_rule_assignment(db_session, word.id, grammar_rule.id)

        assert first.id == second.id
        assert db_session.query(WordRuleAssignment).count() == 1


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


class TestGetOrCreateWordForm:
    def test_returns_existing_form_for_key(self, db_session, language_es, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)

        first = get_or_create_word_form(db_session, assignment.id, row.id, "gato")
        second = get_or_create_word_form(db_session, assignment.id, row.id, "gato")

        assert first.id == second.id
        assert db_session.query(WordForm).count() == 1

    def test_same_form_different_row_creates_distinct_form(self, db_session, language_es, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        row1 = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)
        row2 = create_grammar_rule_row(db_session, grammar_rule.id, "Plural", None, 1, 1)

        form1 = get_or_create_word_form(db_session, assignment.id, row1.id, "gato")
        form2 = get_or_create_word_form(db_session, assignment.id, row2.id, "gato")

        assert form1.id != form2.id


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


class TestGetOrCreateWordFormTranslation:
    def test_returns_existing_form_translation_for_pair(self, db_session, language_es, language_en, word_category, grammar_rule):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)
        form = create_word_form(db_session, assignment.id, row.id, "gato")

        first = get_or_create_word_form_translation(db_session, form.id, language_en.id, "cat")
        second = get_or_create_word_form_translation(db_session, form.id, language_en.id, "cat")

        assert first.id == second.id
        assert db_session.query(WordFormTranslation).count() == 1


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


class TestCountSavedData:
    def test_counts_sentences_word_forms_and_distinct_base_words(
        self, db_session, language_es, language_en, word_category, grammar_rule
    ):
        create_sentence(db_session, "El gato duerme", language_es.id, word_category.id, grammar_rule.id, 0)
        create_sentence(db_session, "La gata duerme", language_es.id, word_category.id, grammar_rule.id, 1)

        gato = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, gato.id, grammar_rule.id)
        row = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)
        create_word_form(db_session, assignment.id, row.id, "gato")
        create_word_form(db_session, assignment.id, row.id, "gata")

        counts = count_saved_data(db_session, grammar_rule.id)

        assert counts == {"sentences": 2, "word_forms": 2, "base_words": 1}

    def test_count_is_scoped_to_the_rule(self, db_session, language_es, word_category, grammar_rule):
        other_rule = GrammarRule(
            name="Other",
            description="Other",
            language_id=grammar_rule.language_id,
            word_category_id=word_category.id,
        )
        db_session.add(other_rule)
        db_session.commit()
        db_session.refresh(other_rule)

        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        create_word_rule_assignment(db_session, word.id, other_rule.id)

        counts = count_saved_data(db_session, grammar_rule.id)

        assert counts == {"sentences": 0, "word_forms": 0, "base_words": 0}

    def test_same_base_word_counted_once_across_multiple_assignments(
        self, db_session, language_es, word_category, grammar_rule
    ):
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        create_word_rule_assignment(db_session, word.id, grammar_rule.id)

        counts = count_saved_data(db_session, grammar_rule.id)

        assert counts["base_words"] == 1
