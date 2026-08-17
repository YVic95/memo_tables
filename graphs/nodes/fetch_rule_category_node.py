from graphs.states import GenerateTableState
from crud.rules import get_grammar_rule_by_id, get_word_category_by_id


def fetch_rule_category_node(state: GenerateTableState) -> GenerateTableState:
    rule = get_grammar_rule_by_id(state["db"], state["grammar_rule_id"])
    if rule is None:
        raise ValueError(f"Grammar rule {state['grammar_rule_id']} not found")

    category = get_word_category_by_id(state["db"], rule.word_category_id)
    slug = category.slug if category else None

    return {
        **state,
        "rule_name": rule.name,
        "rule_description": rule.description,
        "word_category_slug": slug,
    }
