import uuid

import pytest

from graphs.models import TableData, TableRow
from graphs.nodes.generate_category_table_node import (
    generate_category_table_node,
    is_special_topic_adjective_rule,
)
from graphs.prompts import (
    generate_adjective_gender_table_prompt,
    generate_adjective_number_table_prompt,
    generate_adjective_other_table_prompt,
    generate_noun_table_prompt,
    generate_table_prompt,
    generate_verb_table_prompt,
)
from tests.graphs.generation_helpers import (
    ADJ_AGREEMENT_TABLE,
    ADJ_GENDER_TABLE,
    ADJ_NUMBER_TABLE,
    ADJ_OTHER_TABLE,
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
    NOUN_NUMBER_HEADERS,
    PROMPT_VARIABLES,
    FakeNounLayoutLLM,
    FakeSequentialLLM,
    FakeStructuredLLM,
)

LAYOUT_HEADERS = {
    "noun_number": NOUN_NUMBER_HEADERS,
    "noun_gender": NOUN_GENDER_HEADERS,
}


def _state(
    word_category_slug: str,
    *,
    rule_name: str | None = None,
    rule_description: str | None = None,
) -> dict:
    return {
        "db": None,
        "grammar_rule_id": uuid.uuid4(),
        "native_language": PROMPT_VARIABLES["native_language"],
        "target_language": PROMPT_VARIABLES["target_language"],
        "rule_name": rule_name or PROMPT_VARIABLES["rule_name"],
        "rule_description": rule_description or PROMPT_VARIABLES["rule_description"],
        "word_category_slug": word_category_slug,
        "should_fragment": None,
        "fragmented_tables": None,
    }


def _run_node(monkeypatch, state: dict, fake_llm):
    monkeypatch.setattr(
        "graphs.nodes.generate_category_table_node.llm", fake_llm
    )
    result = generate_category_table_node(state)
    return result, fake_llm.prompts[0]


class TestGenerateCategoryTableNode:
    def test_noun_slug_uses_noun_prompt(self, monkeypatch):
        result, prompt = _run_node(
            monkeypatch, _state("noun"), FakeStructuredLLM(NOUN_GENDER_TABLE)
        )

        assert prompt == generate_noun_table_prompt.format(**PROMPT_VARIABLES)
        assert result["general_tables"] == [NOUN_GENDER_TABLE.model_dump()]

    def test_verb_slug_still_uses_verb_prompt(self, monkeypatch):
        result, prompt = _run_node(
            monkeypatch, _state("verb"), FakeStructuredLLM(NOUN_GENDER_TABLE)
        )

        assert prompt == generate_verb_table_prompt.format(**PROMPT_VARIABLES)
        assert result["general_tables"] == [NOUN_GENDER_TABLE.model_dump()]

    @pytest.mark.parametrize("word_category_slug", ["adverb", "pronoun", "unknown"])
    def test_unregistered_slug_falls_back_to_generic_prompt(
        self, monkeypatch, word_category_slug
    ):
        _, prompt = _run_node(
            monkeypatch,
            _state(word_category_slug),
            FakeStructuredLLM(NOUN_GENDER_TABLE),
        )

        assert prompt == generate_table_prompt.format(**PROMPT_VARIABLES)


class TestNounLayoutSelection:
    @pytest.mark.parametrize(
        "rule_name,rule_description,expected_layout,min_pairs,max_pairs",
        [
            pytest.param(
                "Noun Plurals",
                "How nouns form the plural",
                "noun_number",
                2,
                3,
                id="number-rule",
            ),
            pytest.param(
                "Noun Gender",
                "Masculine vs feminine",
                "noun_gender",
                2,
                3,
                id="gender-rule",
            ),
            pytest.param(
                "Gender and Number",
                "Masculine and feminine nouns in singular and plural",
                "noun_number",
                4,
                6,
                id="mixed-rule",
            ),
        ],
    )
    def test_noun_rule_carries_its_layout(
        self,
        monkeypatch,
        rule_name,
        rule_description,
        expected_layout,
        min_pairs,
        max_pairs,
    ):
        state = _state(
            "noun", rule_name=rule_name, rule_description=rule_description
        )

        result, prompt = _run_node(monkeypatch, state, FakeNounLayoutLLM())

        expected_prompt = generate_noun_table_prompt.format(
            **{
                **PROMPT_VARIABLES,
                "rule_name": rule_name,
                "rule_description": rule_description,
            }
        )
        assert prompt == expected_prompt

        table = result["general_tables"][0]
        assert table["noun_table_layout"] == expected_layout
        assert table["headers"] == LAYOUT_HEADERS[expected_layout]
        assert len(table["headers"]) == 8
        assert all(len(row["cells"]) == 8 for row in table["rows"])
        assert min_pairs <= len(table["rows"]) <= max_pairs


class TestNounTableValidation:
    def test_noun_table_without_a_layout_is_rejected(self, monkeypatch):
        table = NOUN_GENDER_TABLE.model_copy(update={"noun_table_layout": None})

        with pytest.raises(ValueError, match="noun_table_layout"):
            _run_node(monkeypatch, _state("noun"), FakeStructuredLLM(table))

    def test_noun_table_with_a_wrong_header_count_is_rejected(self, monkeypatch):
        table = NOUN_GENDER_TABLE.model_copy(
            update={"headers": ["Masculino", "Traducción"]}
        )

        with pytest.raises(ValueError, match="8 columns"):
            _run_node(monkeypatch, _state("noun"), FakeStructuredLLM(table))

    def test_noun_table_with_a_seven_cell_row_is_rejected(self, monkeypatch):
        table = NOUN_GENDER_TABLE.model_copy(
            update={"rows": [TableRow(cells=["el libro"] * 7)]}
        )

        with pytest.raises(ValueError, match="8 cells"):
            _run_node(monkeypatch, _state("noun"), FakeStructuredLLM(table))

    def test_non_noun_table_does_not_need_a_layout(self, monkeypatch):
        table = TableData(
            title="Verbos",
            headers=["Forma", "Ejemplo"],
            rows=[TableRow(cells=["hablo", "Hablo mucho."])],
        )

        result, _ = _run_node(
            monkeypatch, _state("verb"), FakeStructuredLLM(table)
        )

        assert result["general_tables"][0]["noun_table_layout"] is None


class TestAdjectiveTableGeneration:
    def _run_adjective(self, monkeypatch):
        fake_llm = FakeSequentialLLM([ADJ_NUMBER_TABLE, ADJ_GENDER_TABLE])
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def test_adjective_slug_runs_the_number_then_gender_prompts(self, monkeypatch):
        result, fake_llm = self._run_adjective(monkeypatch)

        assert fake_llm.prompts[0] == generate_adjective_number_table_prompt.format(
            **PROMPT_VARIABLES
        )
        assert fake_llm.prompts[1] == generate_adjective_gender_table_prompt.format(
            **PROMPT_VARIABLES,
            avoid_phrases=(
                "el libro rojo, los libros rojos, "
                "el dólar fuerte, los dólares fuertes"
            ),
        )

    def test_adjective_slug_returns_both_general_tables(self, monkeypatch):
        result, _ = self._run_adjective(monkeypatch)

        assert "general_table" not in result
        assert result["general_tables"] == [
            ADJ_NUMBER_TABLE.model_dump(),
            ADJ_GENDER_TABLE.model_dump(),
        ]

    def test_adjective_tables_use_different_phrases(self, monkeypatch):
        _, fake_llm = self._run_adjective(monkeypatch)

        for phrase in ("el libro rojo", "los libros rojos", "el dólar fuerte"):
            assert phrase in fake_llm.prompts[1]

    def test_adjective_table_without_a_layout_is_rejected(self, monkeypatch):
        table = ADJ_NUMBER_TABLE.model_copy(update={"adjective_table_layout": None})

        with pytest.raises(ValueError, match="adjective_table_layout"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeSequentialLLM([table, ADJ_GENDER_TABLE]),
            )

    def test_adjective_table_with_a_wrong_header_count_is_rejected(self, monkeypatch):
        table = ADJ_NUMBER_TABLE.model_copy(
            update={"headers": list(ADJ_NUMBER_TABLE.headers[:7])}
        )

        with pytest.raises(ValueError, match="8 columns"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeSequentialLLM([table, ADJ_GENDER_TABLE]),
            )

    def test_adjective_table_with_a_seven_cell_row_is_rejected(self, monkeypatch):
        table = ADJ_NUMBER_TABLE.model_copy(
            update={"rows": [TableRow(cells=["el libro *rojo*"] * 7)]}
        )

        with pytest.raises(ValueError, match="8 cells"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeSequentialLLM([table, ADJ_GENDER_TABLE]),
            )


class TestAdjectiveAgreementTable:
    def _run_agreement(self, monkeypatch):
        fake_llm = FakeStructuredLLM(ADJ_AGREEMENT_TABLE)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def test_agreement_choice_yields_a_single_general_table(self, monkeypatch):
        result, fake_llm = self._run_agreement(monkeypatch)

        assert len(fake_llm.prompts) == 1
        assert "general_table" not in result
        assert result["general_tables"] == [ADJ_AGREEMENT_TABLE.model_dump()]

    def test_agreement_table_uses_the_entry_prompt(self, monkeypatch):
        _, fake_llm = self._run_agreement(monkeypatch)

        assert fake_llm.prompts[0] == generate_adjective_number_table_prompt.format(
            **PROMPT_VARIABLES
        )


class TestNounPromptContent:
    def test_offers_both_layouts_and_records_the_choice(self):
        template = generate_noun_table_prompt.template

        assert "noun_table_layout" in template
        assert "noun_number" in template
        assert "noun_gender" in template
        assert "NUMBER LAYOUT" in template
        assert "GENDER LAYOUT" in template

    def test_mixed_rules_use_the_number_layout(self):
        template = generate_noun_table_prompt.template

        assert "If the rule covers BOTH gender and number, use the NUMBER layout" in template

    def test_requires_eight_columns_and_eight_cells_per_row(self):
        template = generate_noun_table_prompt.template

        assert "Every row must have exactly eight cells" in template
        assert "Do not add, omit, reorder, or split any of the eight columns" in template

    def test_requires_the_single_and_multi_pattern_pair_counts(self):
        template = generate_noun_table_prompt.template

        assert "Single-pattern rule: generate 2-3 pairs" in template
        assert "Multi-pattern rule: generate 4-6 pairs" in template

    def test_keeps_title_and_headers_in_the_target_language(self):
        template = generate_noun_table_prompt.template

        assert "Table title: written in {target_language}" in template
        assert "Column headers: written in {target_language}" in template

    def test_keeps_translations_and_explanations_in_the_native_language(self):
        template = generate_noun_table_prompt.template

        assert "Translation cells: written in {native_language}" in template
        assert "Explanation cells: written in {native_language}" in template

    def test_requires_translation_articles_and_target_language_examples(self):
        template = generate_noun_table_prompt.template

        assert "include the article" in template
        assert "Example cells: exactly one short sentence in {target_language}" in template
        assert "Do not include a native-language translation in the cell" in template


class TestAdjectivePromptContent:
    def test_number_prompt_describes_the_singular_plural_columns(self):
        template = generate_adjective_number_table_prompt.template

        assert "adjective_table_layout" in template
        assert '"adj_number_gender"' in template
        assert "NUMBER LAYOUT" in template
        assert "1. Singular" in template
        assert "5. Plural" in template

    def test_gender_prompt_describes_the_masculine_feminine_columns(self):
        template = generate_adjective_gender_table_prompt.template

        assert "adjective_table_layout" in template
        assert '"adj_number_gender"' in template
        assert "GENDER LAYOUT" in template
        assert "1. Masculine" in template
        assert "5. Feminine" in template

    def test_both_prompts_require_carrier_phrases_without_markers(self):
        for template in (
            generate_adjective_number_table_prompt.template,
            generate_adjective_gender_table_prompt.template,
        ):
            assert "carrier noun" in template
            assert "Never list a bare adjective" in template
            assert "definite article" in template
            assert "a DIFFERENT adjective in each row" in template
            assert "*rojo*" not in template
            assert "*roja*" not in template

    def test_number_prompt_shows_plain_singular_plural_exemplars(self):
        template = generate_adjective_number_table_prompt.template

        assert "el libro rojo / los libros rojos" in template

    def test_gender_prompt_shows_plain_masculine_feminine_exemplars(self):
        template = generate_adjective_gender_table_prompt.template

        assert "el libro rojo / la mesa roja" in template

    def test_both_prompts_require_eight_cells_and_pair_counts(self):
        for template in (
            generate_adjective_number_table_prompt.template,
            generate_adjective_gender_table_prompt.template,
        ):
            assert "exactly eight cells" in template
            assert "Single-pattern rule: generate 2-3 pairs" in template
            assert "Multi-pattern rule: generate 4-6 pairs" in template
            assert "distinct title" in template

    def test_entry_prompt_scopes_cell_counts_per_layout(self):
        template = generate_adjective_number_table_prompt.template

        assert (
            "Number and agreement layouts: every row must have exactly eight cells"
            in template
        )
        assert (
            "Other layout: every row must have exactly four cells" in template
        )

    def test_gender_prompt_avoids_the_number_table_phrases(self):
        template = generate_adjective_gender_table_prompt.template

        assert "{avoid_phrases}" in template
        assert "Do not reuse these adjectives or carrier nouns" in template

    def test_entry_prompt_offers_the_number_and_agreement_tables(self):
        template = generate_adjective_number_table_prompt.template

        assert "CHOOSE THE TABLE" in template
        assert '"adj_number_gender"' in template
        assert '"adj_agreement"' in template
        assert "AGREEMENT LAYOUT" in template

    def test_entry_prompt_routes_both_dimensions_to_agreement(self):
        template = generate_adjective_number_table_prompt.template

        assert "If the rule covers BOTH gender and number" in template
        assert "use the AGREEMENT table" in template

    def test_agreement_section_describes_full_phrases_in_masculine_feminine(self):
        template = generate_adjective_number_table_prompt.template

        assert "1. Masculine" in template
        assert "5. Feminine" in template
        assert "el libro rojo / la mesa roja" in template
        assert "**el libro" not in template
        assert "*roja*" not in template
        assert "one adjective in its masculine and feminine forms" in template

    def test_entry_prompt_offers_the_other_table(self):
        template = generate_adjective_number_table_prompt.template

        assert '"adj_other"' in template
        assert "OTHER LAYOUT" in template
        for topic in (
            "demonstrative",
            "possessive",
            "comparative",
            "superlative",
            "apocope",
            "indefinite",
            "interrogative",
            "ordinal",
        ):
            assert topic in template.lower()

    def test_other_choice_takes_precedence_for_closed_sets(self):
        template = generate_adjective_number_table_prompt.template

        assert "ALWAYS use this table for such rules" in template
        assert "even if" in template
        assert "closed set of" in template

    def test_number_and_agreement_are_scoped_to_regular_adjectives(self):
        template = generate_adjective_number_table_prompt.template

        assert "regular adjectives" in template

    def test_gender_prompt_keeps_the_same_adjective_kind(self):
        template = generate_adjective_gender_table_prompt.template

        assert "same KIND of adjectives" in template

    def test_other_section_describes_the_four_columns(self):
        template = generate_adjective_number_table_prompt.template

        assert "1. Adjective" in template
        assert "4. Example" in template
        assert "one row = one form" in template
        assert "every row must have exactly four cells" in template
        assert "there is no row cap" in template
        assert "representative forms" in template


class TestAdjectiveOtherTable:
    def _run_other(self, monkeypatch):
        fake_llm = FakeStructuredLLM(ADJ_OTHER_TABLE)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def test_other_choice_yields_a_single_four_column_table(self, monkeypatch):
        result, fake_llm = self._run_other(monkeypatch)

        assert len(fake_llm.prompts) == 1
        assert "general_table" not in result
        assert result["general_tables"] == [ADJ_OTHER_TABLE.model_dump()]

    def test_special_topic_rule_is_pre_routed_to_the_other_prompt(self, monkeypatch):
        fake_llm = FakeStructuredLLM(ADJ_OTHER_TABLE)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )
        state = _state(
            "adjective",
            rule_name="Possessive adjectives",
            rule_description="Forms agree in gender and number.",
        )

        result = generate_category_table_node(state)

        assert len(fake_llm.prompts) == 1
        assert fake_llm.prompts[0] == generate_adjective_other_table_prompt.format(
            **{
                **PROMPT_VARIABLES,
                "rule_name": "Possessive adjectives",
                "rule_description": "Forms agree in gender and number.",
            }
        )
        assert "general_table" not in result
        assert result["general_tables"][0]["adjective_table_layout"] == "adj_other"
        assert result["general_tables"] == [ADJ_OTHER_TABLE.model_dump()]

    def test_special_topic_keyword_routing_is_scoped_to_spanish(self, monkeypatch):
        fake_llm = FakeSequentialLLM([ADJ_NUMBER_TABLE, ADJ_GENDER_TABLE])
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )
        state = _state(
            "adjective",
            rule_name="Comparative Adjectives",
            rule_description="",
        )
        state["target_language"] = "French"

        generate_category_table_node(state)

        assert len(fake_llm.prompts) == 2
        assert fake_llm.prompts[0] == generate_adjective_number_table_prompt.format(
            **{
                **PROMPT_VARIABLES,
                "target_language": "French",
                "rule_name": "Comparative Adjectives",
            }
        )

    @pytest.mark.parametrize(
        "name",
        [
            "Demonstrative Adjectives",
            "Possessive Adjectives",
            "Comparative Adjectives",
            "Superlative Adjectives",
            "Absolute Superlative",
            "Irregular Comparatives",
            "Apocope of Adjectives",
            "Indefinite Adjectives",
            "Interrogative Adjectives",
            "Ordinal Adjectives",
        ],
    )
    def test_routes_spanish_catalog_special_topics_to_other(self, name):
        assert is_special_topic_adjective_rule(name, "")

    @pytest.mark.parametrize(
        "name",
        [
            "Singular and Plural of adjectives",
            "Gender of Adjectives",
            "Noun-Adjective Agreement",
        ],
    )
    def test_does_not_route_regular_inflection_rules_to_other(self, name):
        assert not is_special_topic_adjective_rule(
            name, "Regular adjective forms and agreement"
        )

    def test_detects_special_topic_in_the_rule_description(self):
        assert is_special_topic_adjective_rule(
            "Adjectives", "Demonstrative forms vary by gender and number."
        )

    def test_other_table_with_a_wrong_header_count_is_rejected(self, monkeypatch):
        table = ADJ_OTHER_TABLE.model_copy(
            update={"headers": list(ADJ_OTHER_TABLE.headers[:3])}
        )

        with pytest.raises(ValueError, match="4 columns"):
            _run_node(monkeypatch, _state("adjective"), FakeStructuredLLM(table))

    def test_other_table_with_a_three_cell_row_is_rejected(self, monkeypatch):
        table = ADJ_OTHER_TABLE.model_copy(
            update={"rows": [TableRow(cells=["Este", "this", "near me"])]}
        )

        with pytest.raises(ValueError, match="4 cells"):
            _run_node(monkeypatch, _state("adjective"), FakeStructuredLLM(table))
