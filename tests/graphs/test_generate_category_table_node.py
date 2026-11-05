import uuid

import pytest

from graphs.models import TableData, TableRow
from graphs.nodes.generate_category_table_node import generate_category_table_node
from graphs.prompts import (
    generate_noun_table_prompt,
    generate_table_prompt,
    generate_verb_table_prompt,
)
from tests.graphs.generation_helpers import (
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
    NOUN_NUMBER_HEADERS,
    PROMPT_VARIABLES,
    FakeNounLayoutLLM,
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
        "general_table": None,
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
        assert result["general_table"] == NOUN_GENDER_TABLE.model_dump()

    def test_verb_slug_still_uses_verb_prompt(self, monkeypatch):
        _, prompt = _run_node(
            monkeypatch, _state("verb"), FakeStructuredLLM(NOUN_GENDER_TABLE)
        )

        assert prompt == generate_verb_table_prompt.format(**PROMPT_VARIABLES)

    @pytest.mark.parametrize("word_category_slug", ["adjective", "adverb", "pronoun", "unknown"])
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

        table = result["general_table"]
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

        assert result["general_table"]["noun_table_layout"] is None


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
