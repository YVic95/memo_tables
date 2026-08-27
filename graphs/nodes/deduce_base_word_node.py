from graphs.llm import llm
from graphs.models import DeducedBaseWords
from graphs.prompts import deduce_base_word_prompt
from graphs.states import SaveTableState
from crud.rules import get_grammar_rule_by_id
from crud.language_pairs import get_language_name_by_id

deduce_llm = llm.with_structured_output(DeducedBaseWords)
deduce_chain = deduce_base_word_prompt | deduce_llm


def _extract_unique_forms(tables: list[dict]) -> list[str]:
    forms: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            for cell in row.get("cells", []):
                stripped = cell.strip()
                if stripped:
                    forms.add(stripped)
    return sorted(forms)


def deduce_base_word_node(state: SaveTableState) -> SaveTableState:
    unique_forms = _extract_unique_forms(state["tables"])

    if not unique_forms:
        return {
            **state,
            "base_words_to_save": [],
        }

    rule = get_grammar_rule_by_id(state["db"], state["grammar_rule_id"])
    if rule is None:
        raise ValueError(f"Grammar rule {state['grammar_rule_id']} not found")

    target_language_name = get_language_name_by_id(state["db"], state["target_language_id"])

    result: DeducedBaseWords = deduce_chain.invoke(
        {
            "word_category": state["word_category_slug"],
            "target_language": target_language_name,
            "inflected_forms": "\n".join(unique_forms),
        }
    )

    base_words = [
        {
            "text": word,
            "language_id": state["target_language_id"],
            "word_category_id": rule.word_category_id,
        }
        for word in result.base_words
    ]

    return {
        **state,
        "base_words_to_save": base_words,
    }
