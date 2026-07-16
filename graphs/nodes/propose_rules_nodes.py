from graphs.llm import llm
from graphs.models import ProposedRules
from graphs.prompts import propose_rules_prompt
from graphs.states import RuleCreationAgentState

rule_proposer_llm = llm.with_structured_output(ProposedRules)

def propose_rules_node(state: RuleCreationAgentState):
    prompt = propose_rules_prompt.format(
        native_language=state["native_language"],
        target_language=state["target_language"],
    )

    result: ProposedRules = rule_proposer_llm.invoke(prompt)

    return {
        **state,
        "proposed_rules": [rule.model_dump() for rule in result.rules],
    }