from graphs.llm import llm
from graphs.prompts import rule_content_prompt
from graphs.states import InitialRuleState

def generate_rule_content_node(state: InitialRuleState) -> InitialRuleState:
    pipe = rule_content_prompt | llm
    result = pipe.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_title": state["rule_title"],
        "rule_explanation": state["rule_explanation"],
    })   
    print(f"Result is: {result.content}")
    return {
        **state,
        "full_content": result.content,
    }