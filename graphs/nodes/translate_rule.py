from graphs.llm import llm
from graphs.models import RuleTranslation
from graphs.prompts import translate_prompt
from graphs.states import InitialRuleState

translator_llm = llm.with_structured_output(RuleTranslation)
translate_chain = translate_prompt | translator_llm

def translate_rule_node(state: InitialRuleState) -> InitialRuleState:
    result: RuleTranslation = translate_chain.invoke(
        {
            "native_language": state["native_language"],
            "rule_title": state["rule_title"],
            "rule_explanation": state["rule_explanation"],
        }
    )

    return {
        **state,
        "translated_name": result.name,
        "translated_description": result.description,
    }