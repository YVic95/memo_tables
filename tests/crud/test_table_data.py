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


class TestGetTableData:
    def test_returns_empty_list_when_no_data(self, db_session, grammar_rule):
        from crud.table_data import get_table_data

        result = get_table_data(db_session, grammar_rule.id)

        assert result == []

    def test_single_table_single_word(self, db_session, grammar_rule, language_es, word_category):
        from crud.table_data import get_table_data

        row = create_grammar_rule_row(db_session, grammar_rule.id, "Nominative", None, 1, 0)
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        create_word_form(db_session, assignment.id, row.id, "gato")

        result = get_table_data(db_session, grammar_rule.id)

        assert len(result) == 1
        assert result[0]["table_no"] == 1
        assert len(result[0]["entries"]) == 1
        assert result[0]["entries"][0]["label"] == "Nominative"
        assert result[0]["entries"][0]["base_word_text"] == "gato"
        assert result[0]["entries"][0]["form"] == "gato"

    def test_multiple_tables_grouped_by_table_no(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data

        row1 = create_grammar_rule_row(db_session, grammar_rule.id, "Nominative", None, 1, 0)
        row2 = create_grammar_rule_row(db_session, grammar_rule.id, "Accusative", None, 2, 0)
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        create_word_form(db_session, assignment.id, row1.id, "gato")
        create_word_form(db_session, assignment.id, row2.id, "gato")

        result = get_table_data(db_session, grammar_rule.id)

        assert len(result) == 2
        table_nos = [g["table_no"] for g in result]
        assert table_nos == [1, 2]
        assert len(result[0]["entries"]) == 1
        assert result[0]["entries"][0]["label"] == "Nominative"
        assert len(result[1]["entries"]) == 1
        assert result[1]["entries"][0]["label"] == "Accusative"

    def test_multiple_base_words_create_multiple_entries(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data

        row = create_grammar_rule_row(db_session, grammar_rule.id, "Nominative", None, 1, 0)
        gato = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        perro = get_or_create_base_word(db_session, "perro", language_es.id, word_category.id)
        assign_gato = create_word_rule_assignment(db_session, gato.id, grammar_rule.id)
        assign_perro = create_word_rule_assignment(db_session, perro.id, grammar_rule.id)
        create_word_form(db_session, assign_gato.id, row.id, "gato")
        create_word_form(db_session, assign_perro.id, row.id, "perro")

        result = get_table_data(db_session, grammar_rule.id)

        assert len(result) == 1
        assert result[0]["table_no"] == 1
        entries = result[0]["entries"]
        assert len(entries) == 2
        base_word_texts = {e["base_word_text"] for e in entries}
        assert base_word_texts == {"gato", "perro"}
        for e in entries:
            assert e["form"] is not None

    def test_row_without_word_form_returns_none_for_form(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data

        row = create_grammar_rule_row(db_session, grammar_rule.id, "Nominative", None, 1, 0)
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        create_word_rule_assignment(db_session, word.id, grammar_rule.id)

        result = get_table_data(db_session, grammar_rule.id)

        assert len(result) == 1
        assert result[0]["entries"][0]["form"] is None

    def test_mixed_form_and_no_form_in_same_table(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data

        row = create_grammar_rule_row(db_session, grammar_rule.id, "Nominative", None, 1, 0)
        gato = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        perro = get_or_create_base_word(db_session, "perro", language_es.id, word_category.id)
        assign_gato = create_word_rule_assignment(db_session, gato.id, grammar_rule.id)
        assign_perro = create_word_rule_assignment(db_session, perro.id, grammar_rule.id)
        create_word_form(db_session, assign_gato.id, row.id, "gato")

        result = get_table_data(db_session, grammar_rule.id)

        assert len(result) == 1
        entries = result[0]["entries"]
        assert len(entries) == 2
        forms = {e["base_word_text"]: e["form"] for e in entries}
        assert forms["gato"] == "gato"
        assert forms["perro"] is None

    def test_rows_sorted_by_position_within_table(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data

        row_high = create_grammar_rule_row(db_session, grammar_rule.id, "Plural", None, 1, 2)
        row_low = create_grammar_rule_row(db_session, grammar_rule.id, "Singular", None, 1, 0)
        row_mid = create_grammar_rule_row(db_session, grammar_rule.id, "Dual", None, 1, 1)
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        create_word_form(db_session, assignment.id, row_high.id, "gatos")
        create_word_form(db_session, assignment.id, row_low.id, "gato")
        create_word_form(db_session, assignment.id, row_mid.id, "gatoos")

        result = get_table_data(db_session, grammar_rule.id)

        labels = [e["label"] for e in result[0]["entries"]]
        assert labels == ["Singular", "Dual", "Plural"]

    def test_different_grammar_rules_are_isolated(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data
        from models.grammar_rules import GrammarRule

        other_rule = GrammarRule(
            name="Other",
            description="Other",
            language_id=grammar_rule.language_id,
            word_category_id=word_category.id,
        )
        db_session.add(other_rule)
        db_session.commit()
        db_session.refresh(other_rule)

        row = create_grammar_rule_row(db_session, grammar_rule.id, "Nominative", None, 1, 0)
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        create_word_form(db_session, assignment.id, row.id, "gato")

        result = get_table_data(db_session, other_rule.id)

        assert result == []

    def test_table_no_zero_works_for_non_fragmented(
        self, db_session, grammar_rule, language_es, word_category
    ):
        from crud.table_data import get_table_data

        row = create_grammar_rule_row(db_session, grammar_rule.id, "Default", None, 0, 0)
        word = get_or_create_base_word(db_session, "gato", language_es.id, word_category.id)
        assignment = create_word_rule_assignment(db_session, word.id, grammar_rule.id)
        create_word_form(db_session, assignment.id, row.id, "gato")

        result = get_table_data(db_session, grammar_rule.id)

        assert len(result) == 1
        assert result[0]["table_no"] == 0
        assert result[0]["entries"][0]["label"] == "Default"
        assert result[0]["entries"][0]["form"] == "gato"


class TestBuildMarkdownTables:
    def test_returns_empty_string_for_empty_input(self):
        from crud.table_data import build_markdown_tables

        result = build_markdown_tables([], "verb")

        assert result == {"verb": ""}

    def test_single_table_single_word(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "Singular", "base_word_text": "gato", "form": "gato"},
                    {"label": "Plural", "base_word_text": "gato", "form": "gatos"},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "noun")

        expected = (
            "| Label    | Noun: gato |\n"
            "| -------- | ---------- |\n"
            "| Singular | gato       |\n"
            "| Plural   | gatos      |"
        )
        assert result == {"noun": expected}

    def test_single_table_multiple_words(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "Singular", "base_word_text": "gato", "form": "gato"},
                    {"label": "Singular", "base_word_text": "perro", "form": "perro"},
                    {"label": "Plural", "base_word_text": "gato", "form": "gatos"},
                    {"label": "Plural", "base_word_text": "perro", "form": "perros"},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "noun")

        expected = (
            "| Label    | Noun: gato | Noun: perro |\n"
            "| -------- | ---------- | ----------- |\n"
            "| Singular | gato       | perro       |\n"
            "| Plural   | gatos      | perros      |"
        )
        assert result == {"noun": expected}

    def test_multiple_tables_separated_by_blank_lines(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "Singular", "base_word_text": "gato", "form": "gato"},
                ],
            },
            {
                "table_no": 2,
                "entries": [
                    {"label": "Nominative", "base_word_text": "gato", "form": "gato"},
                ],
            },
        ]

        result = build_markdown_tables(table_data, "noun")

        table1 = (
            "| Label    | Noun: gato |\n"
            "| -------- | ---------- |\n"
            "| Singular | gato       |"
        )
        table2 = (
            "| Label      | Noun: gato |\n"
            "| ---------- | ---------- |\n"
            "| Nominative | gato       |"
        )
        assert result == {"noun": f"{table1}\n\n{table2}"}

    def test_empty_cells_for_none_forms(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "Singular", "base_word_text": "gato", "form": "gato"},
                    {"label": "Singular", "base_word_text": "perro", "form": None},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "noun")

        expected = (
            "| Label    | Noun: gato | Noun: perro |\n"
            "| -------- | ---------- | ----------- |\n"
            "| Singular | gato       |             |"
        )
        assert result == {"noun": expected}

    def test_rows_preserve_entry_order(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "Plural", "base_word_text": "gato", "form": "gatos"},
                    {"label": "Singular", "base_word_text": "gato", "form": "gato"},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "noun")

        lines = result["noun"].split("\n")
        row_labels = [line.split("|")[1].strip() for line in lines[2:]]
        assert row_labels == ["Plural", "Singular"]

    def test_column_headers_use_category_prefix(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "1st", "base_word_text": "hablar", "form": "hablo"},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "verb")

        header_line = result["verb"].split("\n")[0]
        assert "Verb: hablar" in header_line

    def test_result_keyed_by_category_slug(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "1st", "base_word_text": "hablar", "form": "hablo"},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "verb")

        assert "verb" in result
        assert len(result) == 1

    def test_underscore_slug_becomes_title_case_header(self):
        from crud.table_data import build_markdown_tables

        table_data = [
            {
                "table_no": 1,
                "entries": [
                    {"label": "1st", "base_word_text": "hablar", "form": "hablo"},
                ],
            }
        ]

        result = build_markdown_tables(table_data, "reflexive_verb")

        header_line = result["reflexive_verb"].split("\n")[0]
        assert "Reflexive Verb: hablar" in header_line


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
