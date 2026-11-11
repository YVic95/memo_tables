from langgraph.graph import END

from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from models.word_categories import WordCategory

from graphs.models import TableData

from graphs.generate_table_graph import graph, route_after_table
from graphs.prompts import (
    generate_adjective_number_table_prompt,
    generate_adjective_other_table_prompt,
    generate_noun_table_prompt,
)
from tests.graphs.generation_helpers import (
    ADJ_AGREEMENT_TABLE,
    ADJ_GENDER_TABLE,
    ADJ_NUMBER_TABLE,
    ADJ_OTHER_TABLE,
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
    NOUN_NUMBER_TABLE,
    PROMPT_VARIABLES,
    FakeSequentialLLM,
    FakeStructuredLLM,
)


def _adjective_grammar_rule(db_session, language_es, language_en):
    category = WordCategory(name="Adjectives", slug="adjective")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    canonical = CanonicalRule(
        native_language_id=language_en.id,
        target_language_id=language_es.id,
        word_category_id=category.id,
        level="A1",
        name="Adjective Number and Gender",
        description="Adjectives agree in number and gender",
        position=1,
        slug="adj-number-gender",
        is_active=True,
    )
    db_session.add(canonical)
    db_session.commit()
    db_session.refresh(canonical)
    rule = GrammarRule(
        name="Adjective Number and Gender",
        description="Adjectives agree in number and gender",
        language_id=language_es.id,
        word_category_id=category.id,
        canonical_rule_id=canonical.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


class TestAdjectiveTableGeneration:
    def test_adjective_rule_yields_two_generals_and_four_fragments(
        self, monkeypatch, db_session, language_es, language_en
    ):
        rule = _adjective_grammar_rule(db_session, language_es, language_en)
        fake_llm = FakeSequentialLLM([ADJ_NUMBER_TABLE, ADJ_GENDER_TABLE])
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )

        result = graph.invoke({
            "db": db_session,
            "grammar_rule_id": rule.id,
            "native_language": PROMPT_VARIABLES["native_language"],
            "target_language": PROMPT_VARIABLES["target_language"],
        })

        assert result["word_category_slug"] == "adjective"
        assert "general_table" not in result
        assert result["general_tables"] == [
            ADJ_NUMBER_TABLE.model_dump(),
            ADJ_GENDER_TABLE.model_dump(),
        ]
        assert fake_llm.prompts[0] == generate_adjective_number_table_prompt.format(
            **{
                **PROMPT_VARIABLES,
                "rule_name": "Adjective Number and Gender",
                "rule_description": "Adjectives agree in number and gender",
            }
        )

        assert result["should_fragment"] is True
        singular, plural, masculine, feminine = result["fragmented_tables"]
        assert singular["title"] == f"{ADJ_NUMBER_TABLE.title} — Singular"
        assert plural["title"] == f"{ADJ_NUMBER_TABLE.title} — Plural"
        assert masculine["title"] == f"{ADJ_GENDER_TABLE.title} — Masculino"
        assert feminine["title"] == f"{ADJ_GENDER_TABLE.title} — Femenino"
        assert [f["adjective_table_layout"] for f in (singular, plural, masculine, feminine)] == [
            "adj_number_gender"
        ] * 4

    def test_agreement_rule_yields_one_general_table_and_two_fragments(
        self, monkeypatch, db_session, language_es, language_en
    ):
        from graphs.table_utils import select_adjective_tables

        rule = _adjective_grammar_rule(db_session, language_es, language_en)
        fake_llm = FakeStructuredLLM(ADJ_AGREEMENT_TABLE)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )

        result = graph.invoke({
            "db": db_session,
            "grammar_rule_id": rule.id,
            "native_language": PROMPT_VARIABLES["native_language"],
            "target_language": PROMPT_VARIABLES["target_language"],
        })

        assert result["word_category_slug"] == "adjective"
        assert "general_table" not in result
        assert result["general_tables"] == [ADJ_AGREEMENT_TABLE.model_dump()]
        assert len(fake_llm.prompts) == 1

        assert result["should_fragment"] is True
        masculine, feminine = result["fragmented_tables"]
        assert masculine["title"] == f"{ADJ_AGREEMENT_TABLE.title} — Masculino"
        assert feminine["title"] == f"{ADJ_AGREEMENT_TABLE.title} — Femenino"

        merged = select_adjective_tables(
            [
                ADJ_AGREEMENT_TABLE,
                *[TableData(**f) for f in result["fragmented_tables"]],
            ]
        )
        assert len(merged) == 1
        assert [row.cells for row in merged[0].rows] == [
            row.cells for row in ADJ_AGREEMENT_TABLE.rows
        ]
        assert merged[0].adjective_table_layout == "adj_agreement"


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
        assert "general_table" not in result
        assert result["general_tables"] == [NOUN_GENDER_TABLE.model_dump()]
        table = result["general_tables"][0]
        assert table["noun_table_layout"] == "noun_gender"
        assert table["headers"] == NOUN_GENDER_HEADERS
        assert all(len(row["cells"]) == 8 for row in table["rows"])
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

    def test_generic_generation_stores_its_single_table_in_general_tables(
        self, monkeypatch, db_session, grammar_rule
    ):
        class FakeGenerationChain:
            def invoke(self, _prompt_variables):
                return TableData(
                    title="Generic table",
                    headers=["Form", "Meaning"],
                    rows=[],
                )

        category = db_session.get(WordCategory, grammar_rule.word_category_id)
        category.slug = "preposition"
        db_session.commit()
        monkeypatch.setattr(
            "graphs.nodes.generate_general_table_node.generate_table_chain",
            FakeGenerationChain(),
        )

        result = graph.invoke({
            "db": db_session,
            "grammar_rule_id": grammar_rule.id,
            "native_language": "English",
            "target_language": "Spanish",
        })

        assert result["general_tables"] == [
            {"title": "Generic table", "headers": ["Form", "Meaning"], "rows": [],
             "fragmented_table_id": None, "noun_table_layout": None,
             "adjective_table_layout": None}
        ]
        assert "general_table" not in result


def _generate_table_state(word_category_slug: str, row_count: int) -> dict:
    return {
        "word_category_slug": word_category_slug,
        "general_tables": [{
            "title": "Table",
            "headers": ["A", "B"],
            "rows": [{"cells": ["x", "y"]} for _ in range(row_count)],
        }],
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

    def test_single_table_routing_uses_the_first_general_table(self):
        state = _generate_table_state("verb", 3)
        state["general_tables"].append({
            "title": "Second table",
            "headers": ["A", "B"],
            "rows": [{"cells": ["x", "y"]} for _ in range(5)],
        })

        assert route_after_table(state) == END

    def test_other_categories_keep_the_row_threshold(self):
        assert route_after_table(_generate_table_state("verb", 3)) == END
        assert route_after_table(_generate_table_state("verb", 4)) == "fragment"

    def test_adjective_fragments_like_noun(self):
        assert route_after_table(_generate_table_state("adjective", 0)) == "fragment"
        assert route_after_table(_generate_table_state("adjective", 3)) == "fragment"

    def test_adjective_other_table_never_fragments(self):
        state = _generate_table_state("adjective", 10)
        state["general_tables"][0]["adjective_table_layout"] = "adj_other"

        assert route_after_table(state) == END

    def test_adjective_pair_layouts_always_fragment(self):
        for layout in ("adj_number_gender", "adj_agreement"):
            state = _generate_table_state("adjective", 10)
            state["general_tables"][0]["adjective_table_layout"] = layout

            assert route_after_table(state) == "fragment"

    def test_missing_table_stops(self):
        assert route_after_table({"word_category_slug": "noun", "general_tables": []}) == END


class TestAdjectiveOtherTableGeneration:
    def test_other_rule_yields_exactly_one_four_column_table(
        self, monkeypatch, db_session, language_es, language_en
    ):
        rule = _adjective_grammar_rule(db_session, language_es, language_en)
        rule.name = "Possessive adjectives and agreement"
        rule.description = "Possessive forms agree in number and gender"
        db_session.commit()
        many_rows_table = ADJ_OTHER_TABLE.model_copy(
            update={
                "rows": ADJ_OTHER_TABLE.rows * 3,
            }
        )
        fake_llm = FakeStructuredLLM(many_rows_table)
        monkeypatch.setattr(
            "graphs.nodes.generate_category_table_node.llm", fake_llm
        )

        result = graph.invoke({
            "db": db_session,
            "grammar_rule_id": rule.id,
            "native_language": PROMPT_VARIABLES["native_language"],
            "target_language": PROMPT_VARIABLES["target_language"],
        })

        assert result["word_category_slug"] == "adjective"
        assert "general_table" not in result
        assert result["general_tables"] == [many_rows_table.model_dump()]
        table = result["general_tables"][0]
        assert all(len(row["cells"]) == 4 for row in table["rows"])
        assert table["adjective_table_layout"] == "adj_other"
        assert not result.get("fragmented_tables")
        assert len(fake_llm.prompts) == 1
        assert fake_llm.prompts[0] == generate_adjective_other_table_prompt.format(
            **{
                **PROMPT_VARIABLES,
                "rule_name": rule.name,
                "rule_description": rule.description,
            }
        )
