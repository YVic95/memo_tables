from graphs.states import SaveTableState
from crud.rules import get_grammar_rule_by_id, get_word_category_by_id
from crud.language_pairs import get_language_pair_by_id


def fetch_context_node(state: SaveTableState) -> SaveTableState:
    rule = get_grammar_rule_by_id(state["db"], state["grammar_rule_id"])
    if rule is None:
        raise ValueError(f"Grammar rule {state['grammar_rule_id']} not found")

    category = get_word_category_by_id(state["db"], rule.word_category_id)
    slug = category.slug if category else None

    pair = get_language_pair_by_id(state["db"], state["language_pair_id"])
    if pair is None:
        raise ValueError(f"Language pair {state['language_pair_id']} not found")

    return {
        **state,
        "word_category_slug": slug,
        "target_language_id": pair["target_language_id"],
        "native_language_id": pair["native_language_id"],
    }
