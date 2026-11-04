import uuid
from unittest.mock import patch
import pytest
from graphs.nodes.deduce_base_word_node import (
    deduce_base_word_node,
    _extract_unique_forms,
    _extract_form_cells,
    _extract_example_words,
)
from graphs.models import DeducedBaseWords, DeducedBaseWord
from graphs.prompts import deduce_noun_base_word_prompt
from models.word_categories import WordCategory
from tests.graphs.table_fixtures import NOUN_ROLES, NOUN_TABLE


def _base_words(*entries):
    return DeducedBaseWords(base_words=[DeducedBaseWord(**entry) for entry in entries])


def _base_word(word, word_category_id, *surface_forms):
    return {
        "word": word,
        "word_category_id": word_category_id,
        "surface_forms": list(surface_forms),
    }


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture()
def adjective_category(db_session):
    category = WordCategory(name="Adjectives", slug="adjectives")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


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


VERB_TABLE = {
    "title": "Present Tense",
    "headers": ["Pronoun", "Verb", "Example", "Explanation"],
    "rows": [
        {"cells": ["Yo", "hablo", "Yo hablo con mi amigo", "I speak"]},
        {"cells": ["Tú", "hablas", "Tú hablas con mi hermana", "You speak"]},
    ],
}


class TestExtractVerbForms:
    def test_extracts_form_column_only(self):
        result = _extract_form_cells([VERB_TABLE], {"form": 1})
        assert set(result) == {"hablo", "hablas"}

    def test_deduplicates_across_tables(self):
        tables = [
            {"rows": [{"cells": ["Yo", "hablo", "Yo hablo", "I speak"]}]},
            {"rows": [{"cells": ["Yo", "hablo", "Yo hablo", "I speak"]}]},
        ]
        result = _extract_form_cells(tables, {"form": 1})
        assert result == ["hablo"]

    def test_strips_whitespace(self):
        tables = [{"rows": [{"cells": ["Yo", "  hablo  ", "Yo hablo", "I speak"]}]}]
        result = _extract_form_cells(tables, {"form": 1})
        assert result == ["hablo"]

    def test_skips_empty_cells(self):
        tables = [{"rows": [{"cells": ["Yo", "", "", "I speak"]}]}]
        result = _extract_form_cells(tables, {"form": 1})
        assert result == []

    def test_skips_rows_shorter_than_form_column(self):
        tables = [{"rows": [{"cells": ["Yo", "hablo"]}]}]
        assert _extract_form_cells(tables, {"form": 1}) == ["hablo"]


class TestExtractExampleWords:
    def test_tokenizes_example_sentences(self):
        result = _extract_example_words([VERB_TABLE], {"example": 2})
        expected = {"yo", "hablo", "con", "mi", "amigo", "tú", "hablas", "hermana"}
        assert set(result) == expected

    def test_strips_punctuation_and_normalizes_case(self):
        tables = [{"rows": [{"cells": ["", "", "¡Hola, Amigo!", ""]}]}]
        result = _extract_example_words(tables, {"example": 2})
        assert set(result) == {"hola", "amigo"}

    def test_returns_empty_when_no_examples(self):
        assert _extract_example_words([], {"example": 2}) == []


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


class TestExtractNounForms:
    def test_extracts_form_column_only(self):
        result = _extract_form_cells([NOUN_TABLE], NOUN_ROLES)

        assert result == ["la mesa", "las mesas"]

    def test_strips_whitespace(self):
        tables = [{"rows": [{"cells": ["  la mesa  ", "Feminine", "La mesa es grande"]}]}]

        assert _extract_form_cells(tables, NOUN_ROLES) == ["la mesa"]

    def test_deduplicates_forms_across_rows_and_tables(self):
        tables = [
            {"rows": [{"cells": ["la mesa", "Feminine", "La mesa es grande"]}]},
            {"rows": [{"cells": ["la mesa", "Feminine", "La mesa es grande"]}]},
        ]

        assert _extract_form_cells(tables, NOUN_ROLES) == ["la mesa"]

    def test_skips_empty_forms(self):
        tables = [{"rows": [{"cells": ["", "Feminine", "La mesa es grande"]}]}]

        assert _extract_form_cells(tables, NOUN_ROLES) == []


class TestDeduceBaseWordNode:
    def test_returns_empty_when_no_tables(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, tables=[])
        result = deduce_base_word_node(state)
        assert result["base_words_to_save"] == []

    def test_returns_empty_when_all_cells_empty(self, db_session, grammar_rule):
        state = _make_state(db_session, grammar_rule, tables=[
            {"headers": ["Pronoun", "Verb", "Example", "Explanation"], "rows": [{"cells": ["", "", "", ""]}]},
        ])
        result = deduce_base_word_node(state)
        assert result["base_words_to_save"] == []

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_calls_llm_with_surface_forms_and_categories(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category, adjective_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("hablar", verb_category.id, "hablo", "hablas"),
            _base_word("amigo", adjective_category.id, "amigo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        deduce_base_word_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["target_language"] == "Spanish"
        assert "hablo" in call_kwargs["surface_forms"]
        assert "hablas" in call_kwargs["surface_forms"]
        for token in ("yo", "con", "amigo"):
            assert token in call_kwargs["surface_forms"]
        assert "I speak" not in call_kwargs["surface_forms"]
        assert "Yo" not in call_kwargs["surface_forms"]
        assert str(verb_category.id) in call_kwargs["available_categories"]
        assert str(adjective_category.id) in call_kwargs["available_categories"]
        assert "Nouns (noun)" in call_kwargs["rule_word_category"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_returns_base_words_with_per_word_categories(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category, adjective_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("hablar", verb_category.id, "hablo", "hablas"),
            _base_word("amigo", adjective_category.id, "amigo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        result = deduce_base_word_node(state)

        by_text = {item["text"]: item for item in result["base_words_to_save"]}
        assert by_text["hablar"]["word_category_id"] == verb_category.id
        assert by_text["hablar"]["language_id"] == state["target_language_id"]
        assert by_text["hablar"]["forms"] == ["hablo", "hablas"]
        assert by_text["amigo"]["word_category_id"] == adjective_category.id
        assert by_text["amigo"]["forms"] == ["amigo"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_invalid_category_falls_back_to_rule_category(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("hablar", uuid.uuid4(), "hablo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["word_category_id"] == grammar_rule.word_category_id

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_non_verb_tables_filter_words_to_rule_category(
        self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("gato", uuid.uuid4(), "gato"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="adjective",
            tables=[
                {"headers": ["Form", "Explanation", "Example"], "rows": [{"cells": ["gato", "masculine adjective", "el gato"]}]}
            ],
        )

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["word_category_id"] == grammar_rule.word_category_id

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_preserves_other_state_fields(self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("hablar", verb_category.id, "hablo"),
        )
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        result = deduce_base_word_node(state)

        assert result["session_id"] == "test-session"
        assert result["word_category_slug"] == "verb"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    def test_propagates_llm_errors(self, mock_chain, mock_get_lang, db_session, grammar_rule, verb_category):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.side_effect = RuntimeError("LLM API error")
        state = _make_state(db_session, grammar_rule, tables=[VERB_TABLE])

        with pytest.raises(RuntimeError, match="LLM API error"):
            deduce_base_word_node(state)

    def test_raises_when_grammar_rule_not_found(self, db_session):
        state = _make_state(
            db_session,
            type("FakeRule", (), {"id": uuid.UUID("00000000-0000-0000-0000-000000000000")})(),
            tables=[VERB_TABLE],
        )
        with pytest.raises(ValueError, match="Grammar rule"):
            deduce_base_word_node(state)


class TestDeduceNounBaseWordNode:
    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_uses_noun_chain_and_only_form_cells(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("la mesa", uuid.uuid4(), "la mesa", "las mesas"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=[NOUN_TABLE]
        )

        deduce_base_word_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["target_language"] == "Spanish"
        assert call_kwargs["surface_forms"] == "la mesa\nlas mesas"
        assert "Feminine" not in call_kwargs["surface_forms"]
        assert "La mesa es grande" not in call_kwargs["surface_forms"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_chain")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_does_not_use_the_generic_deduction_chain(
        self, mock_noun_chain, mock_generic_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_noun_chain.invoke.return_value = _base_words(
            _base_word("la mesa", uuid.uuid4(), "la mesa", "las mesas"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=[NOUN_TABLE]
        )

        deduce_base_word_node(state)

        mock_noun_chain.invoke.assert_called_once()
        mock_generic_chain.invoke.assert_not_called()

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_returns_citation_form_grouped_under_rule_category(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("la mesa", uuid.uuid4(), "la mesa", "las mesas"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=[NOUN_TABLE]
        )

        result = deduce_base_word_node(state)

        assert len(result["base_words_to_save"]) == 1
        saved = result["base_words_to_save"][0]
        assert saved["text"] == "la mesa"
        assert saved["word_category_id"] == grammar_rule.word_category_id
        assert saved["language_id"] == state["target_language_id"]
        assert saved["forms"] == ["la mesa", "las mesas"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_merges_separate_base_words_that_share_the_same_noun(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("la mesa", uuid.uuid4(), "la mesa"),
            _base_word("las mesas", uuid.uuid4(), "las mesas"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=[NOUN_TABLE]
        )

        result = deduce_base_word_node(state)

        assert len(result["base_words_to_save"]) == 1
        saved = result["base_words_to_save"][0]
        assert saved["text"] == "la mesa"
        assert saved["forms"] == ["la mesa", "las mesas"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_adds_form_cells_the_model_omitted(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("la mesa", uuid.uuid4(), "la mesa"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=[NOUN_TABLE]
        )

        result = deduce_base_word_node(state)

        saved = result["base_words_to_save"][0]
        assert saved["forms"] == ["la mesa", "las mesas"]

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_prefers_the_definite_singular_form_over_the_model_citation(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("las mesas", uuid.uuid4(), "las mesas"),
        )
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=[NOUN_TABLE]
        )

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["text"] == "la mesa"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_maps_an_indefinite_form_to_the_definite_citation(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("mesa", uuid.uuid4(), "una mesa"),
        )
        tables = [
            {"rows": [{"cells": ["una mesa", "Femenino", "Una mesa es grande"]}]},
        ]
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=tables
        )

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["text"] == "la mesa"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_keeps_singular_nouns_that_end_in_s(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("el lunes", uuid.uuid4(), "el lunes"),
        )
        tables = [
            {"rows": [{"cells": ["el lunes", "Masculino", "El lunes es tranquilo"]}]},
        ]
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=tables
        )

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"][0]["text"] == "el lunes"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_repeated_noun_forms_are_deduplicated_before_deduction(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        mock_get_lang.return_value = "Spanish"
        mock_chain.invoke.return_value = _base_words(
            _base_word("la mesa", uuid.uuid4(), "la mesa"),
        )
        tables = [
            {"rows": [NOUN_TABLE["rows"][0], NOUN_TABLE["rows"][0]]},
        ]
        state = _make_state(
            db_session, grammar_rule, word_category_slug="noun", tables=tables
        )

        deduce_base_word_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["surface_forms"] == "la mesa"

    @patch("graphs.nodes.deduce_base_word_node.get_language_name_by_id")
    @patch("graphs.nodes.deduce_base_word_node.deduce_noun_chain")
    def test_returns_empty_when_no_forms(
        self, mock_chain, mock_get_lang, db_session, grammar_rule
    ):
        state = _make_state(
            db_session,
            grammar_rule,
            word_category_slug="noun",
            tables=[
                {"headers": ["Sustantivo", "Explicación", "Ejemplo"], "rows": [{"cells": ["", "", ""]}]},
            ],
        )

        result = deduce_base_word_node(state)

        assert result["base_words_to_save"] == []
        mock_chain.invoke.assert_not_called()


class TestNounDeductionPrompt:
    def test_requests_singular_form_with_the_definite_article(self):
        template = deduce_noun_base_word_prompt.template.lower()

        assert "citation" in template
        assert "singular" in template
        assert "definite article" in template
        assert "indefinite article" in template

    def test_replaces_indefinite_articles_with_the_definite_article(self):
        template = deduce_noun_base_word_prompt.template

        assert "Replace any indefinite article with the definite article" in template
        assert "strip any indefinite article" not in template

    def test_states_the_rule_category_without_asking_for_a_choice(self):
        template = deduce_noun_base_word_prompt.template

        assert "Use this word category for every base word" in template
        assert "assign it a word category" not in template
        assert "Every base word must be assigned" not in template

    def test_instructs_the_model_to_group_surface_forms(self):
        template = deduce_noun_base_word_prompt.template

        assert "Group every surface form" in template

    def test_restricts_surface_forms_to_the_form_column(self):
        template = deduce_noun_base_word_prompt.template

        assert "Given the forms from a noun table" in template
        assert "Never treat explanation prose or example sentences" in template
