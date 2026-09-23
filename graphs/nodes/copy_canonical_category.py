from crud.canonical_rules import get_canonical_rule_by_id
from graphs.states import InitialRuleState


def copy_canonical_category_node(state: InitialRuleState) -> InitialRuleState:
    """Copy the word category from the catalog entry the rule was chosen from.

    No classification LLM runs here: the canonical catalog already knows the
    category, so the persisted rule inherits it through the catalog link.
    """
    canonical_rule = get_canonical_rule_by_id(state["db"], state["canonical_rule_id"])
    if canonical_rule is None:
        raise ValueError(
            f"Canonical rule {state['canonical_rule_id']} not found"
        )

    return {
        **state,
        "word_category_id": canonical_rule.word_category_id,
    }
