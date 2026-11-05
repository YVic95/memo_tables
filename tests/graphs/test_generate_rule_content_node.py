from langchain_core.messages import AIMessage

import graphs.nodes.generate_rule_content as content_module
from graphs.nodes.generate_rule_content import generate_rule_content_node
from graphs.prompts import noun_rule_content_prompt, rule_content_prompt

PROMPT_VARIABLES = {
    "native_language": "English",
    "target_language": "Spanish",
    "rule_title": "Singular and Plural of nouns",
    "rule_explanation": "Nouns change form to show one or more than one.",
}


def _state(word_category_slug: str | None) -> dict:
    return {
        **PROMPT_VARIABLES,
        "word_category_slug": word_category_slug,
    }


class FakeContentLLM:
    def __init__(self, content: str = "## generated"):
        self.content = content
        self.prompts: list[str] = []

    def __call__(self, prompt_value):
        self.prompts.append(prompt_value.to_string())
        return AIMessage(content=self.content)


class TestGenerateRuleContentNode:
    def test_noun_rule_uses_the_noun_prompt(self, monkeypatch):
        fake_llm = FakeContentLLM()
        monkeypatch.setattr(content_module, "llm", fake_llm)

        result = generate_rule_content_node(_state("noun"))

        assert fake_llm.prompts == [
            noun_rule_content_prompt.format(**PROMPT_VARIABLES)
        ]
        assert result["full_content"] == "## generated"

    def test_non_noun_rule_keeps_the_general_prompt(self, monkeypatch):
        fake_llm = FakeContentLLM()
        monkeypatch.setattr(content_module, "llm", fake_llm)

        result = generate_rule_content_node(_state("verb"))

        assert fake_llm.prompts == [rule_content_prompt.format(**PROMPT_VARIABLES)]
        assert result["full_content"] == "## generated"

    def test_missing_category_falls_back_to_the_general_prompt(self, monkeypatch):
        fake_llm = FakeContentLLM()
        monkeypatch.setattr(content_module, "llm", fake_llm)

        generate_rule_content_node(_state(None))

        assert fake_llm.prompts == [rule_content_prompt.format(**PROMPT_VARIABLES)]


class TestNounRuleContentPrompt:
    def test_allows_multiple_nouns_instead_of_one_lexical_item(self):
        template = noun_rule_content_prompt.template

        assert "Use 4-5 examples" in template
        assert "DIFFERENT noun (or noun pair) in each example" in template
        assert "Do not use only one noun" in template
        assert "Select ONE representative lexical item" not in template

    def test_requires_each_example_on_a_single_line(self):
        template = noun_rule_content_prompt.template

        assert "Each numbered example MUST be a single line" in template
        assert "multi-line item breaks the numbering" in template

    def test_requires_definite_articles_on_every_noun(self):
        template = noun_rule_content_prompt.template

        assert "Every noun MUST appear with its definite article" in template
        assert "Never list a bare noun" in template
        assert "**el libro / los libros**" in template
        assert "**el dólar / los dólares**" in template

    def test_keeps_the_shared_heading_and_formatting_structure(self):
        template = noun_rule_content_prompt.template

        assert "## Grammar Rule: {rule_title}" in template
        assert "### Rule Statement:" in template
        assert "### Examples:" in template
        assert "numbered lists (1. 2. ...)" in template

    def test_general_prompt_keeps_its_single_item_instruction(self):
        assert "Select ONE representative lexical item" in rule_content_prompt.template
