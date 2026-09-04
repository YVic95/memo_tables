import uuid
from unittest.mock import patch
import pytest
from graphs.models import DeducedBaseWords, DeducedBaseWord, TranslationPair, Translations
from graphs.save_table_graph import graph
from models.language_pairs import LanguagePair
from models.word_categories import WordCategory
from models.grammar_rules import GrammarRule


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


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture()
def seeded_context(db_session, language_es, language_en, verb_category):
    pair = LanguagePair(
        native_language_id=language_en.id,
        target_language_id=language_es.id,
    )
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)

    rule = GrammarRule(
        name="Present Tense",
        description="Regular -ar verbs",
        language_id=language_es.id,
        word_category_id=verb_category.id,
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
