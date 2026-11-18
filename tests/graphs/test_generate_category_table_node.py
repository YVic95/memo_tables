import re
import uuid
from dataclasses import replace

import pytest

from graphs.models import TableData, TableRow
from graphs.category_table_config import (
    CATEGORY_CONFIG,
)
from graphs.nodes.generate_category_table_node import generate_category_table_node
from graphs.table_validators import validate_noun_table
from graphs.prompts import (
    choose_adjective_table_prompt,
    generate_adjective_gender_table_prompt,
    generate_adjective_gender_or_agreement_table_prompt,
    generate_adjective_number_table_prompt,
    generate_adjective_other_table_prompt,
    generate_noun_table_prompt,
    generate_table_prompt,
    generate_verb_table_prompt,
)
from tests.graphs.generation_helpers import (
    ADJ_AGREEMENT_NUMBER_TABLE,
    ADJ_AGREEMENT_TABLE,
    ADJ_GENDER_TABLE,
    ADJ_NUMBER_TABLE,
    ADJ_OTHER_TABLE,
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
    NOUN_NUMBER_HEADERS,
    PROMPT_VARIABLES,
    FakeAdjectiveLLM,
    FakeNounLayoutLLM,
    FakeRuleTextAdjectiveLLM,
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
        "graphs.table_generator.llm", fake_llm
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

    def test_category_config_selects_its_validator(self, monkeypatch):
        table = TableData(
            title="Verbos",
            headers=["Forma", "Ejemplo"],
            rows=[TableRow(cells=["hablo", "Hablo mucho."])],
        )
        monkeypatch.setitem(
            CATEGORY_CONFIG,
            "verb",
            replace(CATEGORY_CONFIG["verb"], validator=validate_noun_table),
        )

        with pytest.raises(ValueError, match="noun_table_layout"):
            _run_node(monkeypatch, _state("verb"), FakeStructuredLLM(table))


class TestAdjectiveTableGeneration:
    def _run_number(self, monkeypatch):
        fake_llm = FakeAdjectiveLLM("adj_number", [ADJ_NUMBER_TABLE])
        monkeypatch.setattr(
            "graphs.table_generator.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def _run_gender(self, monkeypatch):
        fake_llm = FakeAdjectiveLLM("adj_gender", [ADJ_GENDER_TABLE])
        monkeypatch.setattr(
            "graphs.table_generator.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def test_adjective_slug_classifies_then_runs_number_prompt(
        self, monkeypatch
    ):
        result, fake_llm = self._run_number(monkeypatch)

        assert fake_llm.classifier_prompts[0] == (
            choose_adjective_table_prompt.format(
                rule_name=PROMPT_VARIABLES["rule_name"],
                rule_description=PROMPT_VARIABLES["rule_description"],
            )
        )
        assert fake_llm.table_prompts[0] == (
            generate_adjective_number_table_prompt.format(**PROMPT_VARIABLES)
        )
        assert len(fake_llm.table_prompts) == 1

    def test_gender_choice_runs_standalone_gender_prompt(
        self, monkeypatch
    ):
        _, fake_llm = self._run_gender(monkeypatch)

        assert fake_llm.table_prompts[0] == (
            generate_adjective_gender_table_prompt.format(**PROMPT_VARIABLES)
        )
        assert len(fake_llm.table_prompts) == 1

    def test_gender_prompt_takes_no_avoid_variables(self):
        assert set(generate_adjective_gender_table_prompt.input_variables) == {
            "native_language",
            "target_language",
            "rule_name",
            "rule_description",
        }

    def test_number_prompt_takes_no_avoid_variables(self):
        assert set(generate_adjective_number_table_prompt.input_variables) == {
            "native_language",
            "target_language",
            "rule_name",
            "rule_description",
        }

    def test_classifier_input_is_rule_text_only(self, monkeypatch):
        _, fake_llm = self._run_number(monkeypatch)

        classifier_prompt = fake_llm.classifier_prompts[0]
        assert PROMPT_VARIABLES["rule_name"] in classifier_prompt
        assert PROMPT_VARIABLES["rule_description"] in classifier_prompt
        assert PROMPT_VARIABLES["native_language"] not in classifier_prompt
        assert PROMPT_VARIABLES["target_language"] not in classifier_prompt

    def test_adjective_slug_returns_a_single_general_table(self, monkeypatch):
        result, _ = self._run_number(monkeypatch)

        assert "general_table" not in result
        assert result["general_tables"] == [
            ADJ_NUMBER_TABLE.model_copy(
                update={"title": PROMPT_VARIABLES["rule_name"]}
            ).model_dump()
        ]

    def test_gender_choice_returns_a_single_general_table(self, monkeypatch):
        result, _ = self._run_gender(monkeypatch)

        assert "general_table" not in result
        assert result["general_tables"] == [
            ADJ_GENDER_TABLE.model_copy(
                update={"title": PROMPT_VARIABLES["rule_name"]}
            ).model_dump()
        ]

    def test_number_and_gender_outputs_mark_only_form_cells(self, monkeypatch):
        for run in (self._run_number, self._run_gender):
            result, _ = run(monkeypatch)

            for table in result["general_tables"]:
                for row in table["rows"]:
                    assert all("*" in row["cells"][index] for index in (0, 4))
                    assert all(
                        "*" not in row["cells"][index]
                        for index in (1, 2, 3, 5, 6, 7)
                    )

    def test_number_and_gender_tables_use_different_adjectives(self, monkeypatch):
        self._run_number(monkeypatch)
        self._run_gender(monkeypatch)

        def bare_tokens(table):
            tokens = set()
            for row in table.rows:
                for index in (0, 4):
                    cell = row.cells[index]
                    match = re.search(r"\*([^*]+)\*", cell)
                    tokens.add((match.group(1) if match else cell).strip().lower())
            return tokens

        assert bare_tokens(ADJ_NUMBER_TABLE).isdisjoint(bare_tokens(ADJ_GENDER_TABLE))

    def test_adjective_table_without_a_layout_is_rejected(self, monkeypatch):
        table = ADJ_NUMBER_TABLE.model_copy(update={"adjective_table_layout": None})

        with pytest.raises(ValueError, match="adjective_table_layout"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeAdjectiveLLM("adj_number", [table]),
            )

    def test_adjective_table_with_a_wrong_header_count_is_rejected(self, monkeypatch):
        table = ADJ_NUMBER_TABLE.model_copy(
            update={"headers": list(ADJ_NUMBER_TABLE.headers[:7])}
        )

        with pytest.raises(ValueError, match="8 columns"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeAdjectiveLLM("adj_number", [table]),
            )

    def test_adjective_table_with_a_seven_cell_row_is_rejected(self, monkeypatch):
        table = ADJ_NUMBER_TABLE.model_copy(
            update={"rows": [TableRow(cells=["el libro *rojo*"] * 7)]}
        )

        with pytest.raises(ValueError, match="8 cells"):
            _run_node(
                monkeypatch, _state("adjective"), FakeAdjectiveLLM("adj_number", [table])
            )

    def test_generator_layout_mismatch_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="Generator layout mismatch"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeAdjectiveLLM("adj_number", [ADJ_AGREEMENT_TABLE]),
            )


class TestAdjectiveAgreementTable:
    def _run_agreement(self, monkeypatch):
        fake_llm = FakeAdjectiveLLM(
            "adj_agreement",
            [ADJ_AGREEMENT_NUMBER_TABLE, ADJ_AGREEMENT_TABLE],
        )
        monkeypatch.setattr(
            "graphs.table_generator.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def test_agreement_choice_yields_two_general_tables(self, monkeypatch):
        result, fake_llm = self._run_agreement(monkeypatch)

        assert len(fake_llm.classifier_prompts) == 1
        assert len(fake_llm.table_prompts) == 2
        assert "general_table" not in result
        assert [t["adjective_table_layout"] for t in result["general_tables"]] == [
            "adj_agreement_number",
            "adj_agreement_gender",
        ]
        assert result["general_tables"][0]["title"] == "Noun Gender by number"
        assert result["general_tables"][1]["title"] == "Noun Gender by gender"

    def test_agreement_output_marks_only_form_cells(self, monkeypatch):
        result, _ = self._run_agreement(monkeypatch)

        for table in result["general_tables"]:
            for row in table["rows"]:
                assert "*" in row["cells"][0]
                assert "*" in row["cells"][4]
                assert all(
                    "*" not in row["cells"][index]
                    for index in (1, 2, 3, 5, 6, 7)
                )

    def test_agreement_gender_companion_receives_avoid_list(
        self, monkeypatch
    ):
        _, fake_llm = self._run_agreement(monkeypatch)

        assert fake_llm.table_prompts[0] == (
            generate_adjective_number_table_prompt.format(**PROMPT_VARIABLES)
        )
        # The companion receives the entry table's phrases as {avoid_phrases}.
        assert "el coche" in fake_llm.table_prompts[1].lower() or "azul" in fake_llm.table_prompts[1].lower()
        assert PROMPT_VARIABLES["rule_name"] in fake_llm.table_prompts[1]


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
    def test_adjective_form_cells_mark_only_the_adjective(self):
        marker_instruction = (
            "Form cells: wrap only the target-language adjective itself in "
            "single asterisks"
        )
        for prompt in (
            generate_adjective_number_table_prompt,
            generate_adjective_gender_table_prompt,
            generate_adjective_gender_or_agreement_table_prompt,
            generate_adjective_other_table_prompt,
        ):
            normalized = " ".join(prompt.template.split())
            assert marker_instruction in normalized
            assert "Example cells remain unmarked" in normalized

    def test_choose_prompt_offers_new_plumbing_layouts(self):
        template = choose_adjective_table_prompt.template

        assert '"adj_other"' in template
        assert '"adj_number"' in template
        assert '"adj_gender"' in template
        # Agreement is one classifier choice fanning out to both generals.
        assert '"adj_agreement"' in template
        assert '"adj_agreement_number"' in template
        assert '"adj_agreement_gender"' in template
        assert '"adj_number_gender"' not in template

    def test_choose_prompt_takes_only_rule_text(self):
        variables = set(choose_adjective_table_prompt.input_variables)

        assert variables == {"rule_name", "rule_description"}

    def test_choose_prompt_decides_semantically_from_name(self):
        template = choose_adjective_table_prompt.template

        assert "Decide semantically" in template
        assert "mainly from the rule NAME" in template
        assert "description only" in template
        assert "clarifies" in template

    def test_choose_prompt_has_no_first_match_keyword_logic(self):
        template = choose_adjective_table_prompt.template

        assert "Choose the first layout" not in template
        assert "first layout that applies" not in template.lower()

    def test_choose_prompt_prioritizes_other_number_gender_agreement(self):
        template = choose_adjective_table_prompt.template

        assert '"adj_other"' in template
        assert '"adj_number"' in template
        assert '"adj_gender"' in template
        assert "default fallback" in template.lower()
        # Other wins even when gender/number are mentioned.
        assert "even if" in template.lower()
        assert "gender" in template.lower() and "number" in template.lower()

    def test_choose_prompt_distinguishes_number_gender_by_invariance(self):
        template = choose_adjective_table_prompt.template.lower()

        assert "gender-invariant" in template
        assert "number-invariant" in template
        assert "both" in template

    def test_choose_prompt_falls_back_to_agreement_for_generic_names(self):
        template = choose_adjective_table_prompt.template

        assert "generic names" in template.lower() or "fallback" in template.lower()
        assert "Adjetivos" in template or "adjetivos" in template.lower()

    def test_choose_prompt_lists_special_adjective_topics(self):
        template = choose_adjective_table_prompt.template.lower()

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
            assert topic in template

    def test_choose_prompt_routes_agreement_mention_with_special_topic_to_other(self):
        template = choose_adjective_table_prompt.template

        # OTHER is checked first and wins even when gender/number are mentioned.
        assert "even if" in template.lower()
        assert "gender" in template.lower() and "number" in template.lower()

    def test_number_prompt_describes_singular_plural_columns(self):
        template = generate_adjective_number_table_prompt.template

        assert "adjective_table_layout" in template
        assert '"adj_number"' in template
        assert '"adj_agreement_number"' in template
        assert "NUMBER LAYOUT" in template
        assert "1. Singular" in template
        assert "5. Plural" in template
        assert '"adj_other"' not in template

    def test_gender_prompt_describes_the_masculine_feminine_columns(self):
        template = generate_adjective_gender_table_prompt.template

        assert "adjective_table_layout" in template
        assert '"adj_gender"' in template
        assert '"adj_agreement_gender"' not in template
        assert "GENDER LAYOUT" in template
        assert "1. Masculine" in template
        assert "5. Feminine" in template

    def test_gender_prompt_has_no_avoid_list(self):
        template = generate_adjective_gender_table_prompt.template

        assert "{avoid_phrases}" not in template
        assert "avoid" not in template.lower()

    def test_agreement_companion_prompt_describes_the_masculine_feminine_columns(self):
        template = generate_adjective_gender_or_agreement_table_prompt.template

        assert "adjective_table_layout" in template
        assert '"adj_agreement_gender"' in template
        assert "1. Masculine" in template
        assert "5. Feminine" in template

    def test_gender_prompt_is_standalone_single_general(self):
        template = generate_adjective_gender_table_prompt.template
        normalized = " ".join(template.split())

        assert "standalone" in template.lower()
        assert "single-general" in template.lower()
        assert "{avoid_phrases}" not in template
        assert "companion" not in template.lower()

    def test_agreement_companion_prompt_keeps_the_avoid_list(self):
        template = generate_adjective_gender_or_agreement_table_prompt.template
        normalized = " ".join(template.split())

        assert "AGREEMENT by-gender" in template
        assert "{avoid_phrases}" in template
        assert "Do not reuse these adjectives or carrier nouns" in template
        assert "same kind" in normalized

    def test_single_general_prompts_require_carrier_phrases_and_mark_only_the_adjective(self):
        for template in (
            generate_adjective_number_table_prompt.template,
            generate_adjective_gender_table_prompt.template,
            generate_adjective_gender_or_agreement_table_prompt.template,
        ):
            normalized = " ".join(template.split())
            assert "carrier noun" in template
            assert "Never list a bare adjective" in template
            assert "definite article" in template
            assert "a DIFFERENT adjective in each row" in template
            assert "*rojo*" in template
            assert "Do not mark the surrounding noun or any other words" in normalized

        assert "*roja*" in (
            generate_adjective_gender_table_prompt.template
        )
        assert "*roja*" in (
            generate_adjective_gender_or_agreement_table_prompt.template
        )

    def test_number_prompt_shows_marked_singular_plural_exemplars(self):
        template = generate_adjective_number_table_prompt.template

        assert "el libro *rojo* / los libros *rojos*" in template

    def test_gender_prompt_shows_marked_masculine_feminine_exemplars(self):
        template = generate_adjective_gender_table_prompt.template

        assert "el libro *rojo* / la mesa *roja*" in template

    def test_agreement_companion_shows_marked_masculine_feminine_exemplars(self):
        template = generate_adjective_gender_or_agreement_table_prompt.template

        assert "el libro *rojo* / la mesa *roja*" in template

    def test_single_general_prompts_require_eight_cells_and_pair_counts(self):
        for template in (
            generate_adjective_number_table_prompt.template,
            generate_adjective_gender_table_prompt.template,
            generate_adjective_gender_or_agreement_table_prompt.template,
        ):
            assert "exactly eight cells" in template
            assert "Single-pattern rule: generate 2-3 pairs" in template
            assert "Multi-pattern rule: generate 4-6 pairs" in template

    def test_single_general_prompts_use_the_rule_name_verbatim(self):
        number_template = generate_adjective_number_table_prompt.template
        assert "rule name verbatim" in number_template.lower()
        gender_template = generate_adjective_gender_table_prompt.template
        assert "rule name verbatim" in gender_template.lower()
        assert "by gender" not in gender_template.lower()
        assert "concordancia" in gender_template.lower()

    def test_agreement_prompts_derive_by_number_and_by_gender_titles(self):
        number_template = generate_adjective_number_table_prompt.template
        assert "by number" in number_template.lower()
        companion_template = (
            generate_adjective_gender_or_agreement_table_prompt.template
        )
        assert "by gender" in companion_template.lower()

    def test_number_prompt_states_frozen_gender_and_varying_number(self):
        template = " ".join(
            generate_adjective_number_table_prompt.template.lower().split()
        )

        assert "gender-invariant" in template
        assert "only number changes" in template
        assert "frozen" in template
        assert "varying dimension is number" in template

    def test_number_prompt_allows_mixed_genders_across_rows(self):
        template = " ".join(
            generate_adjective_number_table_prompt.template.lower().split()
        )

        assert "masculine nouns in some rows" in template
        assert "feminine nouns in others" in template
        assert "must name the gender used in that row" in template

    def test_gender_prompt_states_frozen_number_and_varying_gender(self):
        template = " ".join(
            generate_adjective_gender_table_prompt.template.lower().split()
        )

        assert "number-invariant" in template
        assert "only gender changes" in template
        assert "frozen" in template
        assert "varying dimension is gender" in template

    def test_gender_prompt_allows_mixed_numbers_across_rows(self):
        template = " ".join(
            generate_adjective_gender_table_prompt.template.lower().split()
        )

        assert "singular nouns in some rows" in template
        assert "plural nouns in others" in template
        assert "must name the number used in that row" in template

    def test_other_prompt_marks_the_adjective_column_only(self):
        template = " ".join(generate_adjective_other_table_prompt.template.split())

        assert (
            "capitalized target-language form. Form cells: wrap only the "
            "target-language adjective itself"
        ) in template
        assert "single asterisks (for example, *Este*)" in template
        assert "Example cells remain unmarked" in template
        assert "translations and explanations remain unmarked" in template


class TestAdjectiveOtherTable:
    def _run_other(self, monkeypatch):
        fake_llm = FakeAdjectiveLLM("adj_other", [ADJ_OTHER_TABLE])
        monkeypatch.setattr(
            "graphs.table_generator.llm", fake_llm
        )
        return generate_category_table_node(_state("adjective")), fake_llm

    def test_other_choice_yields_a_single_four_column_table(self, monkeypatch):
        result, fake_llm = self._run_other(monkeypatch)

        assert len(fake_llm.classifier_prompts) == 1
        assert len(fake_llm.table_prompts) == 1
        assert "general_table" not in result
        assert result["general_tables"] == [ADJ_OTHER_TABLE.model_dump()]

    def test_other_output_marks_only_the_adjective_column(self, monkeypatch):
        result, _ = self._run_other(monkeypatch)

        for row in result["general_tables"][0]["rows"]:
            assert row["cells"][0].startswith("*") and row["cells"][0].endswith("*")
            assert all("*" not in row["cells"][index] for index in (1, 2, 3))

    def test_classifier_routes_possessive_agreement_mention_to_other(
        self, monkeypatch
    ):
        fake_llm = FakeRuleTextAdjectiveLLM(
            {
                "adj_number": [ADJ_NUMBER_TABLE],
                "adj_gender": [ADJ_GENDER_TABLE],
                "adj_agreement_number": [ADJ_NUMBER_TABLE],
                "adj_agreement_gender": [ADJ_AGREEMENT_TABLE],
                "adj_other": [ADJ_OTHER_TABLE],
            }
        )
        monkeypatch.setattr("graphs.table_generator.llm", fake_llm)
        state = _state(
            "adjective",
            rule_name="Possessive adjectives",
            rule_description="Forms agree in gender and number.",
        )

        result = generate_category_table_node(state)

        assert fake_llm.layouts == ["adj_other"]
        assert fake_llm.table_prompts[0] == (
            generate_adjective_other_table_prompt.format(
                **{
                    **PROMPT_VARIABLES,
                    "rule_name": "Possessive adjectives",
                    "rule_description": "Forms agree in gender and number.",
                }
            )
        )
        assert "general_table" not in result
        assert result["general_tables"][0]["adjective_table_layout"] == "adj_other"
        assert result["general_tables"] == [ADJ_OTHER_TABLE.model_dump()]

    def test_other_routing_has_no_language_fast_path(self, monkeypatch):
        fake_llm = FakeRuleTextAdjectiveLLM(
            {
                "adj_number": [ADJ_NUMBER_TABLE],
                "adj_gender": [ADJ_GENDER_TABLE],
                "adj_agreement_number": [ADJ_NUMBER_TABLE],
                "adj_agreement_gender": [ADJ_AGREEMENT_TABLE],
                "adj_other": [ADJ_OTHER_TABLE],
            }
        )
        monkeypatch.setattr("graphs.table_generator.llm", fake_llm)
        state = _state(
            "adjective",
            rule_name="Comparative Adjectives",
            rule_description="",
        )
        state["target_language"] = "French"

        result = generate_category_table_node(state)

        assert fake_llm.layouts == ["adj_other"]
        assert result["general_tables"] == [ADJ_OTHER_TABLE.model_dump()]

    def test_classifier_lists_catalog_other_topics(self):
        template = choose_adjective_table_prompt.template.lower()

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
            assert topic in template

    def test_classifier_detects_other_topic_in_the_rule_description(
        self, monkeypatch
    ):
        fake_llm = FakeRuleTextAdjectiveLLM(
            {
                "adj_number": [ADJ_NUMBER_TABLE],
                "adj_gender": [ADJ_GENDER_TABLE],
                "adj_agreement_number": [ADJ_NUMBER_TABLE],
                "adj_agreement_gender": [ADJ_AGREEMENT_TABLE],
                "adj_other": [ADJ_OTHER_TABLE],
            }
        )
        monkeypatch.setattr("graphs.table_generator.llm", fake_llm)

        result = generate_category_table_node(
            _state(
                "adjective",
                rule_name="Adjectives",
                rule_description="Demonstrative forms vary by gender and number.",
            )
        )

        assert fake_llm.layouts == ["adj_other"]
        assert result["general_tables"] == [ADJ_OTHER_TABLE.model_dump()]

    def test_classifier_routes_regular_inflection_to_pair_flow(self, monkeypatch):
        for name, expected_layouts, fallback in [
            ("Singular and Plural of adjectives", ["adj_number"], "adj_number"),
            ("Gender of Adjectives", ["adj_gender"], "adj_gender"),
            (
                "Noun-Adjective Agreement",
                ["adj_agreement_number", "adj_agreement_gender"],
                "adj_agreement",
            ),
        ]:
            fake_llm = FakeRuleTextAdjectiveLLM(
                {
                    "adj_number": [ADJ_NUMBER_TABLE.model_copy(deep=True)],
                    "adj_gender": [ADJ_GENDER_TABLE.model_copy(deep=True)],
                    "adj_agreement_number": [
                        ADJ_AGREEMENT_NUMBER_TABLE.model_copy(deep=True)
                    ],
                    "adj_agreement_gender": [
                        ADJ_AGREEMENT_TABLE.model_copy(deep=True)
                    ],
                    "adj_other": [ADJ_OTHER_TABLE.model_copy(deep=True)],
                },
                fallback=fallback,
            )
            monkeypatch.setattr("graphs.table_generator.llm", fake_llm)

            result = generate_category_table_node(
                _state(
                    "adjective",
                    rule_name=name,
                    rule_description="Regular adjective forms and agreement",
                )
            )

            assert fake_llm.layouts[0] != "adj_other"
            assert [t["adjective_table_layout"] for t in result["general_tables"]] == (
                expected_layouts
            )
            if expected_layouts == ["adj_number"] or expected_layouts == ["adj_gender"]:
                assert result["general_tables"][0]["title"] == name
            else:
                assert result["general_tables"][0]["title"] == f"{name} by number"
                assert result["general_tables"][1]["title"] == f"{name} by gender"

    def test_other_table_with_a_wrong_header_count_is_rejected(self, monkeypatch):
        table = ADJ_OTHER_TABLE.model_copy(
            update={"headers": list(ADJ_OTHER_TABLE.headers[:3])}
        )

        with pytest.raises(ValueError, match="4 columns"):
            _run_node(
                monkeypatch,
                _state("adjective"),
                FakeAdjectiveLLM("adj_other", [table]),
            )

    def test_other_table_with_a_three_cell_row_is_rejected(self, monkeypatch):
        table = ADJ_OTHER_TABLE.model_copy(
            update={"rows": [TableRow(cells=["Este", "this", "near me"])]}
        )

        with pytest.raises(ValueError, match="4 cells"):
            _run_node(
                monkeypatch, _state("adjective"), FakeAdjectiveLLM("adj_other", [table])
            )
