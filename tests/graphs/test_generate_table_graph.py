from graphs.generate_table_graph import graph
from graphs.prompts import generate_noun_table_prompt
from tests.graphs.generation_helpers import (
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
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
        assert result.get("fragmented_tables") is None
