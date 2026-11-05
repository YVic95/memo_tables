import uuid
from unittest.mock import patch
import pytest
from graphs.models import DeducedBaseWords, DeducedBaseWord, TranslationPair, Translations
from graphs.save_table_graph import graph
from models.language_pairs import LanguagePair
from models.word_categories import WordCategory
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from tests.graphs.generation_helpers import NOUN_GENDER_TABLE, NOUN_NUMBER_TABLE


class TestDeducedBaseWordValidation:
    def test_surface_forms_are_deduplicated(self):
        result = DeducedBaseWord(
            word="dělat",
            word_category_id=uuid.uuid4(),
            surface_forms=["dělá", "dělám", "dělá", "dělám", "děláš"],
        )
        assert result.surface_forms == ["dělá", "dělám", "děláš"]

    def test_deduplication_is_case_insensitive(self):
        result = DeducedBaseWord(
            word="hablar",
            word_category_id=uuid.uuid4(),
            surface_forms=["Hablo", "hablo", "HABLO"],
        )
        assert result.surface_forms == ["Hablo"]

    def test_no_duplicates_left_unmodified(self):
        forms = ["dělá", "dělám", "děláš", "děláme", "děláte", "dělají"]
        result = DeducedBaseWord(
            word="dělat",
            word_category_id=uuid.uuid4(),
            surface_forms=forms,
        )
        assert result.surface_forms == forms
from models.base_words import BaseWord
from models.word_rule_assignments import WordRuleAssignment
from models.grammar_rule_rows import GrammarRuleRow
from models.word_forms import WordForm
from models.word_translations import WordTranslation
from models.sentences import Sentence
from models.word_form_sentences import WordFormSentence


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _create_language_pair(db_session, language_es, language_en):
    pair = LanguagePair(
        native_language_id=language_en.id,
        target_language_id=language_es.id,
    )
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)
    return pair


@pytest.fixture()
def seeded_context(db_session, language_es, language_en, verb_category):
    pair = _create_language_pair(db_session, language_es, language_en)

    canon = CanonicalRule(
        native_language_id=language_en.id,
        target_language_id=language_es.id,
        word_category_id=verb_category.id,
        level="A1",
        name="Present Tense",
        description="Regular -ar verbs",
        position=1,
        slug="present-tense",
        is_active=True,
    )
    db_session.add(canon)
    db_session.commit()
    db_session.refresh(canon)

    rule = GrammarRule(
        name="Present Tense",
        description="Regular -ar verbs",
        language_id=language_es.id,
        word_category_id=verb_category.id,
        canonical_rule_id=canon.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    return {
        "pair_id": pair.pair_id,
        "rule_id": rule.id,
        "category_id": verb_category.id,
        "target_language_id": language_es.id,
        "native_language_id": language_en.id,
    }


@pytest.fixture()
def noun_seeded_context(db_session, language_es, language_en, grammar_rule):
    pair = _create_language_pair(db_session, language_es, language_en)

    return {
        "pair_id": pair.pair_id,
        "rule_id": grammar_rule.id,
        "category_id": grammar_rule.word_category_id,
        "target_language_id": language_es.id,
        "native_language_id": language_en.id,
    }


def _make_state(db_session, seeded_context, **overrides):
    state = {
        "db": db_session,
        "language_pair_id": seeded_context["pair_id"],
        "session_id": str(uuid.uuid4()),
        "grammar_rule_id": seeded_context["rule_id"],
        "tables": [
            {
                "title": "Presente",
                "headers": ["Pronoun", "Verb", "Example", "Explanation"],
                "rows": [
                    {"cells": ["Yo", "hablo", "Yo hablo", "I speak"], "row_position": 0},
                    {"cells": ["Tú", "hablas", "Tú hablas", "You speak"], "row_position": 1},
                ],
            }
        ],
        "target_language_id": seeded_context["target_language_id"],
        "native_language_id": seeded_context["native_language_id"],
        "word_category_slug": "verb",
        "base_words_to_save": [],
        "form_to_base_word_id": {},
    }
    state.update(overrides)
    return state


def _deduce_result(category_id):
    return DeducedBaseWords(base_words=[
        DeducedBaseWord(
            word="hablar",
            word_category_id=category_id,
            surface_forms=["hablo", "hablas"],
        ),
    ])


class TestGraphStructure:
    def test_compiles_with_the_five_save_nodes(self):
        node_names = set(graph.get_graph().nodes.keys())
        assert {"fetch_context", "deduce_base_word", "save_base_word", "translate_base_words", "process_all_tables"} <= node_names


class TestGraphInvocation:
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_runs_end_to_end_and_persists_tables(
        self, mock_deduce, mock_translate, mock_base_translate, db_session, seeded_context, language_es, language_en
    ):
        mock_base_translate.invoke.return_value = Translations(translations=[
            TranslationPair(text="hablar", translation="to speak"),
        ])
        mock_deduce.invoke.return_value = _deduce_result(seeded_context["category_id"])
        mock_translate.invoke.return_value = Translations(translations=[
            TranslationPair(text="Yo", translation="I"),
            TranslationPair(text="hablo", translation="I speak"),
            TranslationPair(text="Yo hablo", translation="I speak"),
            TranslationPair(text="Tú", translation="You"),
            TranslationPair(text="hablas", translation="You speak"),
            TranslationPair(text="Tú hablas", translation="You speak"),
        ])
        state = _make_state(db_session, seeded_context)

        graph.invoke(state)

        base_word = db_session.query(BaseWord).filter(BaseWord.text == "hablar").one()

        assert db_session.query(WordRuleAssignment).count() == 1

        rows = db_session.query(GrammarRuleRow).order_by(GrammarRuleRow.position).all()
        assert [row.label for row in rows] == ["Yo", "Tú"]

        forms = db_session.query(WordForm).all()
        assert {form.form for form in forms} == {"hablo", "hablas"}

        assert db_session.query(Sentence).count() == 2

        word_translation = db_session.query(WordTranslation).one()
        assert word_translation.base_word_id == base_word.id
        assert word_translation.translation == "to speak"

    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_writes_can_be_rolled_back_after_invoke(
        self, mock_deduce, mock_translate, mock_base_translate, db_session, seeded_context, language_es, language_en
    ):
        mock_deduce.invoke.return_value = _deduce_result(seeded_context["category_id"])
        mock_translate.invoke.return_value = Translations(translations=[])
        mock_base_translate.invoke.return_value = Translations(translations=[])
        state = _make_state(db_session, seeded_context)

        graph.invoke(state)
        db_session.rollback()

        assert db_session.query(BaseWord).count() == 0
        assert db_session.query(GrammarRuleRow).count() == 0
        assert db_session.query(WordTranslation).count() == 0


class TestNounGraphInvocation:
    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_number_table_persists_singular_base_words_and_both_sides(
        self, mock_deduce, mock_translate, mock_base_translate,
        db_session, noun_seeded_context,
    ):
        mock_translate.invoke.return_value = Translations(translations=[
            TranslationPair(text="La mesa es grande.", translation="The table is big."),
            TranslationPair(text="Las mesas son grandes.", translation="The tables are big."),
            TranslationPair(text="El libro es nuevo.", translation="The book is new."),
            TranslationPair(text="Los libros son nuevos.", translation="The books are new."),
        ])
        state = _make_state(
            db_session,
            noun_seeded_context,
            tables=[NOUN_NUMBER_TABLE.model_dump()],
            word_category_slug="noun",
        )

        graph.invoke(state)

        base_words = sorted(db_session.query(BaseWord).all(), key=lambda word: word.text)
        assert [word.text for word in base_words] == ["el libro", "la mesa"]
        assert all(
            word.word_category_id == noun_seeded_context["category_id"]
            for word in base_words
        )
        assert db_session.query(WordRuleAssignment).count() == 2

        rows = db_session.query(GrammarRuleRow).order_by(GrammarRuleRow.position).all()
        assert [row.label for row in rows] == [
            "la mesa", "las mesas", "el libro", "los libros",
        ]
        assert [row.position for row in rows] == [0, 1, 2, 3]

        forms = {form.form for form in db_session.query(WordForm).all()}
        assert forms == {"la mesa", "las mesas", "el libro", "los libros"}
        assert db_session.query(WordFormSentence).count() == 4

        translations = {
            translation.base_word_id: translation.translation
            for translation in db_session.query(WordTranslation).all()
        }
        assert translations[base_words[0].id] == "the book"
        assert translations[base_words[1].id] == "the table"

        mock_deduce.invoke.assert_not_called()
        mock_base_translate.invoke.assert_not_called()

    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_gender_table_persists_masculine_and_feminine_base_words(
        self, mock_translate, mock_base_translate,
        db_session, noun_seeded_context,
    ):
        mock_translate.invoke.return_value = Translations(translations=[])
        state = _make_state(
            db_session,
            noun_seeded_context,
            tables=[NOUN_GENDER_TABLE.model_dump()],
            word_category_slug="noun",
        )

        graph.invoke(state)

        base_words = {word.text for word in db_session.query(BaseWord).all()}
        assert base_words == {"el libro", "la mesa", "el problema", "la mano"}
        assert all(
            word.word_category_id == noun_seeded_context["category_id"]
            for word in db_session.query(BaseWord).all()
        )

        rows = db_session.query(GrammarRuleRow).order_by(GrammarRuleRow.position).all()
        assert [row.label for row in rows] == [
            "el libro", "la mesa", "el problema", "la mano",
        ]
        assert db_session.query(WordFormSentence).count() == 4

    @patch("graphs.nodes.translate_base_words_node.translate_chain")
    @patch("graphs.nodes.process_all_tables_node.translate_chain")
    def test_missing_generated_base_translation_falls_back_to_translate_chain(
        self, mock_translate, mock_base_translate,
        db_session, noun_seeded_context,
    ):
        mock_translate.invoke.return_value = Translations(translations=[])
        mock_base_translate.invoke.return_value = Translations(translations=[
            TranslationPair(text="el libro", translation="the book"),
            TranslationPair(text="la mesa", translation="the table"),
        ])
        table = NOUN_NUMBER_TABLE.model_copy(
            update={
                "rows": [
                    NOUN_NUMBER_TABLE.rows[0].model_copy(
                        update={"cells": ["la mesa", "", "Feminine", "La mesa es grande.", "las mesas", "", "Plural", "Las mesas son grandes."]}
                    ),
                    NOUN_NUMBER_TABLE.rows[1].model_copy(
                        update={"cells": ["el libro", "", "Masculine", "El libro es nuevo.", "los libros", "", "Plural", "Los libros son nuevos."]}
                    ),
                ]
            }
        )
        state = _make_state(
            db_session,
            noun_seeded_context,
            tables=[table.model_dump()],
            word_category_slug="noun",
        )

        graph.invoke(state)

        sent_items = set(mock_base_translate.invoke.call_args[0][0]["items"].splitlines())
        assert sent_items == {"el libro", "la mesa"}
