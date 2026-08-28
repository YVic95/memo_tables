import uuid
from unittest.mock import patch
import pytest
from graphs.nodes.process_all_tables_node import process_all_tables_node
from graphs.models import Translations
from crud.table_data import get_or_create_base_word, create_word_rule_assignment
from models.word_categories import WordCategory
from models.grammar_rules import GrammarRule
from models.grammar_rule_rows import GrammarRuleRow
from models.grammar_rule_row_translations import GrammarRuleRowTranslation
from models.word_forms import WordForm
from models.word_form_translations import WordFormTranslation
from models.word_rule_assignments import WordRuleAssignment
from models.sentences import Sentence
from models.sentence_translations import SentenceTranslation
from models.word_form_sentences import WordFormSentence


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture()
def verb_rule(db_session, language_es, verb_category):
    rule = GrammarRule(
        name="Present Tense",
        description="Regular -ar verbs",
        language_id=language_es.id,
        word_category_id=verb_category.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def _seed_base_word_with_assignment(db_session, rule, language_es, text="hablar"):
    word = get_or_create_base_word(db_session, text, language_es.id, rule.word_category_id)
    create_word_rule_assignment(db_session, word.id, rule.id)
    return word


def _make_state(db_session, rule, language_es, language_en, word_category_slug, **overrides):
    state = {
        "db": db_session,
        "language_pair_id": uuid.uuid4(),
        "session_id": "test-session",
        "grammar_rule_id": rule.id,
        "tables": [],
        "target_language_id": language_es.id,
        "native_language_id": language_en.id,
        "word_category_slug": word_category_slug,
        "base_words_to_save": [],
        "form_to_base_word_id": {},
    }
    state.update(overrides)
    return state


VERB_TABLE = {
    "title": "Presente",
    "headers": ["Pronoun", "Verb", "Example", "Explanation"],
    "rows": [
        {"cells": ["Yo", "hablo", "Yo hablo con mi amigo", "I speak"], "row_position": 0},
        {"cells": ["Tú", "hablas", "Tú hablas con mi hermana", "You speak"], "row_position": 1},
    ],
}

VERB_TRANSLATIONS = Translations(translations={
    "Yo": "I",
    "hablo": "I speak",
    "Yo hablo con mi amigo": "I speak with my friend",
    "Tú": "You",
    "hablas": "You speak",
    "Tú hablas con mi hermana": "You speak with my sister",
    "amigo": "friend",
})

EXPECTED_EXAMPLE_TOKENS = {"yo", "hablo", "con", "mi", "amigo", "tú", "hablas", "hermana"}


class TestVerbTable:
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_creates_rows_for_each_pronoun(self, mock_chain, db_session, verb_rule, language_es, language_en):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={"hablo": word.id, "hablas": word.id},
        )

        process_all_tables_node(state)

        rows = db_session.query(GrammarRuleRow).order_by(GrammarRuleRow.position).all()
        assert [row.label for row in rows] == ["Yo", "Tú"]
        assert [row.description for row in rows] == ["I speak", "You speak"]
        assert all(row.table_no == 0 for row in rows)
        assert [row.position for row in rows] == [0, 1]
        assert all(row.grammar_rule_id == verb_rule.id for row in rows)

    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_creates_row_translations_in_native_language(self, mock_chain, db_session, verb_rule, language_es, language_en):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={"hablo": word.id, "hablas": word.id},
        )

        process_all_tables_node(state)

        translations = db_session.query(GrammarRuleRowTranslation).all()
        assert [t.label_translation for t in translations] == ["I", "You"]
        assert all(t.language_id == language_en.id for t in translations)

    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_creates_word_forms_linked_to_their_base_word_assignment(
        self, mock_chain, db_session, verb_rule, language_es, language_en
    ):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        hablar = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        amigo = _seed_base_word_with_assignment(db_session, verb_rule, language_es, text="amigo")
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={
                "hablo": hablar.id, "hablas": hablar.id, "amigo": amigo.id,
            },
        )

        process_all_tables_node(state)

        hablar_assignment = (
            db_session.query(WordRuleAssignment)
            .filter(WordRuleAssignment.base_word_id == hablar.id).one()
        )
        amigo_assignment = (
            db_session.query(WordRuleAssignment)
            .filter(WordRuleAssignment.base_word_id == amigo.id).one()
        )

        forms = db_session.query(WordForm).join(
            GrammarRuleRow, WordForm.grammar_rule_row_id == GrammarRuleRow.id
        ).order_by(GrammarRuleRow.position).all()
        form_by_text = {form.form: form for form in forms}
        assert set(form_by_text) == {"hablo", "hablas", "amigo"}
        assert form_by_text["hablo"].word_rule_assignment_id == hablar_assignment.id
        assert form_by_text["hablas"].word_rule_assignment_id == hablar_assignment.id
        assert form_by_text["amigo"].word_rule_assignment_id == amigo_assignment.id
        assert all(form.grammar_rule_row_id is not None for form in forms)

    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_creates_word_form_translations_in_native_language(
        self, mock_chain, db_session, verb_rule, language_es, language_en
    ):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        hablar = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        amigo = _seed_base_word_with_assignment(db_session, verb_rule, language_es, text="amigo")
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={
                "hablo": hablar.id, "hablas": hablar.id, "amigo": amigo.id,
            },
        )

        process_all_tables_node(state)

        form_translations = db_session.query(WordFormTranslation).all()
        assert {t.translation for t in form_translations} == {"I speak", "You speak", "friend"}
        assert all(t.language_id == language_en.id for t in form_translations)

    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_example_words_tokenized_and_passed_to_translate_chain(
        self, mock_chain, db_session, verb_rule, language_es, language_en
    ):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={"hablo": word.id, "hablas": word.id},
        )

        process_all_tables_node(state)

        sent_items = mock_chain.invoke.call_args[0][0]["items"]
        for token in EXPECTED_EXAMPLE_TOKENS:
            assert token in sent_items

    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_creates_sentences_and_links_word_forms_to_them(
        self, mock_chain, db_session, verb_rule, language_es, language_en
    ):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        hablar = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        amigo = _seed_base_word_with_assignment(db_session, verb_rule, language_es, text="amigo")
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={
                "hablo": hablar.id, "hablas": hablar.id, "amigo": amigo.id,
            },
        )

        process_all_tables_node(state)

        sentences = db_session.query(Sentence).order_by(Sentence.row_position).all()
        assert [s.template for s in sentences] == [
            "Yo hablo con mi amigo",
            "Tú hablas con mi hermana",
        ]
        assert all(s.language_id == language_es.id for s in sentences)
        assert all(s.word_category_id == verb_rule.word_category_id for s in sentences)

        sentence_translations = db_session.query(SentenceTranslation).all()
        assert {t.template for t in sentence_translations} == {
            "I speak with my friend",
            "You speak with my sister",
        }
        assert all(t.language_id == language_en.id for t in sentence_translations)

        links = db_session.query(WordFormSentence).all()
        linked_forms = {
            form.form
            for link in links
            for form in [db_session.query(WordForm).filter(WordForm.id == link.word_form_id).one()]
        }
        assert linked_forms == {"hablo", "hablas", "amigo"}


class TestGeneralTable:
    GENERAL_TABLE = {
        "title": "Género",
        "headers": ["Form", "Explanation", "Example"],
        "rows": [
            {"cells": ["Masculine", "masculine nouns", "el gato"]},
        ],
    }

    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_creates_label_and_description_no_word_form(self, mock_chain, db_session, grammar_rule, language_es, language_en):
        category = db_session.query(WordCategory).filter(WordCategory.slug == "nouns").one()
        mock_chain.invoke.return_value = Translations(translations={
            "Masculine": "Masculine",
            "el gato": "the cat",
        })
        state = _make_state(
            db_session, grammar_rule, language_es, language_en, category.slug,
            tables=[self.GENERAL_TABLE], form_to_base_word_id={},
        )

        process_all_tables_node(state)

        row = db_session.query(GrammarRuleRow).one()
        assert row.label == "Masculine"
        assert row.description == "masculine nouns"

        assert db_session.query(WordForm).count() == 0
        assert db_session.query(WordFormTranslation).count() == 0
        assert db_session.query(WordFormSentence).count() == 0

        sentence = db_session.query(Sentence).one()
        assert sentence.template == "el gato"
        sentence_translation = db_session.query(SentenceTranslation).one()
        assert sentence_translation.template == "the cat"


class TestFragmentedTables:
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_saves_distinct_table_no_per_fragment(self, mock_chain, db_session, verb_rule, language_es, language_en):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        tables = [
            {
                "title": "Singular",
                "headers": ["Pronoun", "Verb", "Example", "Explanation"],
                "rows": [{"cells": ["Yo", "hablo", "Yo hablo", "I speak"], "row_position": 0}],
                "fragmented_table_id": 1,
            },
            {
                "title": "Plural",
                "headers": ["Pronoun", "Verb", "Example", "Explanation"],
                "rows": [{"cells": ["Nosotros", "hablamos", "Nosotros hablamos", "We speak"], "row_position": 0}],
                "fragmented_table_id": 2,
            },
        ]
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=tables,
            form_to_base_word_id={"hablo": word.id, "hablamos": word.id},
        )

        process_all_tables_node(state)

        table_nos = [row.table_no for row in db_session.query(GrammarRuleRow).all()]
        assert sorted(table_nos) == [1, 2]


class TestTranslationFallback:
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_missing_translation_falls_back_to_source_text(self, mock_chain, db_session, verb_rule, language_es, language_en):
        mock_chain.invoke.return_value = Translations(translations={
            "Yo": "I",
        })
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={"hablo": word.id, "hablas": word.id},
        )

        process_all_tables_node(state)

        row_translations = db_session.query(GrammarRuleRowTranslation).all()
        by_label = {t.label_translation: t for t in row_translations}
        assert by_label["I"].label_translation == "I"
        assert by_label["Tú"].label_translation == "Tú"


class TestRowPosition:
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_uses_row_position_from_payload(self, mock_chain, db_session, verb_rule, language_es, language_en):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        tables = [{
            "title": "Presente",
            "headers": ["Pronoun", "Verb", "Example", "Explanation"],
            "rows": [{"cells": ["Yo", "hablo", "Yo hablo", "I speak"], "row_position": 5}],
        }]
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=tables,
            form_to_base_word_id={"hablo": word.id},
        )

        process_all_tables_node(state)

        assert db_session.query(GrammarRuleRow).one().position == 5


class TestRollback:
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_writes_are_rolled_back(self, mock_chain, db_session, verb_rule, language_es, language_en):
        mock_chain.invoke.return_value = VERB_TRANSLATIONS
        word = _seed_base_word_with_assignment(db_session, verb_rule, language_es)
        state = _make_state(
            db_session, verb_rule, language_es, language_en, "verb",
            tables=[VERB_TABLE],
            form_to_base_word_id={"hablo": word.id, "hablas": word.id},
        )

        process_all_tables_node(state)
        db_session.rollback()

        assert db_session.query(GrammarRuleRow).count() == 0
        assert db_session.query(WordForm).count() == 0
        assert db_session.query(Sentence).count() == 0