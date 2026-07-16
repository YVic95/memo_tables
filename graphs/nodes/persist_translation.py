from graphs.states import InitialRuleState
from crud.rules import create_translation

def persist_translation_node(state: InitialRuleState) -> InitialRuleState:
    create_translation(
        db=state["db"],
        grammar_rule_id=state["grammar_rule_id"],
        language_id=state["native_language_id"],
        name=state["translated_name"],
        description=state["translated_description"],
    )

    return state