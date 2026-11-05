from langgraph.graph import END

from graphs.generate_table_graph import graph, route_after_table
from graphs.prompts import generate_noun_table_prompt
from tests.graphs.generation_helpers import (
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
    NOUN_NUMBER_TABLE,
    PROMPT_VARIABLES,
    FakeStructuredLLM,
)


class TestNounTableGeneration:
    def test_noun_rule_produces_noun_table(self, monkeypatch, db_session, grammar_rule):
        fake_llm = FakeStructuredLLM(NOUN_GENDER_TABLE)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )

        result = graph.invoke({
            "db": db_session,
            "grammar_rule_id": grammar_rule.id,
            "native_language": PROMPT_VARIABLES["native_language"],
            "target_language": PROMPT_VARIABLES["target_language"],
        })

        assert result["word_category_slug"] == "noun"
        assert result["general_table"] == NOUN_GENDER_TABLE.model_dump()
        assert result["general_table"]["noun_table_layout"] == "noun_gender"
        assert result["general_table"]["headers"] == NOUN_GENDER_HEADERS
        assert all(len(row["cells"]) == 8 for row in result["general_table"]["rows"])
        assert fake_llm.prompts[0] == generate_noun_table_prompt.format(**PROMPT_VARIABLES)

        assert result["should_fragment"] is True
        masculine, feminine = result["fragmented_tables"]
        assert masculine["title"] == f"{NOUN_GENDER_TABLE.title} — Masculino"
        assert feminine["title"] == f"{NOUN_GENDER_TABLE.title} — Femenino"
        assert masculine["headers"] == NOUN_GENDER_HEADERS[:4]
        assert feminine["headers"] == NOUN_GENDER_HEADERS[4:]
        assert all(
            len(row["cells"]) == 4
            for fragment in (masculine, feminine)
            for row in fragment["rows"]
        )
        assert masculine["noun_table_layout"] == "noun_gender"
        assert feminine["noun_table_layout"] == "noun_gender"

    def test_single_pair_noun_table_fragments_through_the_graph(
        self, monkeypatch, db_session, grammar_rule
    ):
        single_pair_table = NOUN_NUMBER_TABLE.model_copy(
            update={"rows": [NOUN_NUMBER_TABLE.rows[0]]}
        )
        fake_llm = FakeStructuredLLM(single_pair_table)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )

        result = graph.invoke({
            "db": db_session,
            "grammar_rule_id": grammar_rule.id,
            "native_language": PROMPT_VARIABLES["native_language"],
            "target_language": PROMPT_VARIABLES["target_language"],
        })

        assert result["should_fragment"] is True
        assert len(result["fragmented_tables"]) == 2
        for fragment in result["fragmented_tables"]:
            assert len(fragment["rows"]) == 1
            assert len(fragment["rows"][0]["cells"]) == 4


def _generate_table_state(word_category_slug: str, row_count: int) -> dict:
    return {
        "word_category_slug": word_category_slug,
        "general_table": {
            "title": "Table",
            "headers": ["A", "B"],
            "rows": [{"cells": ["x", "y"]} for _ in range(row_count)],
        },
    }


class TestRouteAfterTable:
    def test_noun_fragments_with_a_single_row(self):
        assert route_after_table(_generate_table_state("noun", 1)) == "fragment"

    def test_noun_fragments_with_no_rows(self):
        assert route_after_table(_generate_table_state("noun", 0)) == "fragment"

    def test_verb_at_threshold_does_not_fragment(self):
        assert route_after_table(_generate_table_state("verb", 3)) == END

    def test_verb_above_threshold_fragments(self):
        assert route_after_table(_generate_table_state("verb", 4)) == "fragment"

    def test_other_categories_keep_the_row_threshold(self):
        assert route_after_table(_generate_table_state("adjective", 3)) == END
        assert route_after_table(_generate_table_state("adjective", 4)) == "fragment"

    def test_missing_table_stops(self):
        assert route_after_table({"word_category_slug": "noun", "general_table": None}) == END
