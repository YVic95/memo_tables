import uuid

import pytest

from graphs.nodes.generate_category_table_node import generate_category_table_node
from graphs.prompts import (
    generate_noun_table_prompt,
    generate_table_prompt,
    generate_verb_table_prompt,
)
from tests.graphs.generation_helpers import (
    NOUN_TABLE,
    PROMPT_VARIABLES,
    FakeStructuredLLM,
)


def _state(word_category_slug: str) -> dict:
    return {
        "db": None,
        "grammar_rule_id": uuid.uuid4(),
        "native_language": PROMPT_VARIABLES["native_language"],
        "target_language": PROMPT_VARIABLES["target_language"],
        "rule_name": PROMPT_VARIABLES["rule_name"],
        "rule_description": PROMPT_VARIABLES["rule_description"],
        "word_category_slug": word_category_slug,
        "general_table": None,
        "should_fragment": None,
        "fragmented_tables": None,
    }


def _run_node(monkeypatch, word_category_slug: str):
    fake_llm = FakeStructuredLLM(NOUN_TABLE)
    monkeypatch.setattr(
        "graphs.nodes.generate_category_table_node.llm", fake_llm
    )
    result = generate_category_table_node(_state(word_category_slug))
    return result, fake_llm.prompts[0]


class TestGenerateCategoryTableNode:
    def test_noun_slug_uses_noun_prompt(self, monkeypatch):
        result, prompt = _run_node(monkeypatch, "noun")

        assert prompt == generate_noun_table_prompt.format(**PROMPT_VARIABLES)
        assert result["general_table"] == NOUN_TABLE.model_dump()

    def test_verb_slug_still_uses_verb_prompt(self, monkeypatch):
        _, prompt = _run_node(monkeypatch, "verb")

        assert prompt == generate_verb_table_prompt.format(**PROMPT_VARIABLES)

    @pytest.mark.parametrize("word_category_slug", ["adjective", "adverb", "pronoun", "unknown"])
    def test_unregistered_slug_falls_back_to_generic_prompt(
        self, monkeypatch, word_category_slug
    ):
        _, prompt = _run_node(monkeypatch, word_category_slug)

        assert prompt == generate_table_prompt.format(**PROMPT_VARIABLES)


class TestNounPromptContent:
    def test_requests_the_noun_column_structure(self):
        template = generate_noun_table_prompt.template

        assert "EXACTLY these three columns" in template
        assert "definite article" in template
        assert "gender" in template
        assert "plural" in template

    def test_requires_an_example_sentence_on_every_row(self):
        template = generate_noun_table_prompt.template

        assert "Every row must include a short example sentence" in template

    def test_keeps_title_and_headers_in_the_target_language(self):
        template = generate_noun_table_prompt.template

        assert "Table title: written in {target_language}" in template
        assert "Column headers: written in {target_language}" in template

    def test_keeps_explanations_in_the_native_language(self):
        template = generate_noun_table_prompt.template

        assert "Explanation text inside cells: written in {native_language}" in template
