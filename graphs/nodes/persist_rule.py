from graphs.states import InitialRuleState
from crud.rules import create_grammar_rule

def persist_rule_node(state: InitialRuleState) -> InitialRuleState:
    rule_id = create_grammar_rule(
        db=state["db"],
        title=state["rule_title"],
        description=state["rule_explanation"],
        language_id=state["target_language_id"],
        word_category_id=state["word_category_id"],
    )

    return {
        **state,
        "grammar_rule_id": rule_id,
    }