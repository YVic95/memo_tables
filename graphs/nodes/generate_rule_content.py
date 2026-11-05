from graphs.llm import llm
from graphs.prompts import noun_rule_content_prompt, rule_content_prompt
from graphs.states import InitialRuleState

CONTENT_PROMPTS = {
    "noun": noun_rule_content_prompt,
}


def generate_rule_content_node(state: InitialRuleState) -> InitialRuleState:
    prompt = CONTENT_PROMPTS.get(state.get("word_category_slug"), rule_content_prompt)
    pipe = prompt | llm
    result = pipe.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_title": state["rule_title"],
        "rule_explanation": state["rule_explanation"],
    })

    return {
        **state,
        "full_content": result.content,
    }
