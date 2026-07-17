from graphs.llm import llm
from graphs.models import ProposedRules
from graphs.prompts import propose_rules_prompt
from graphs.states import RuleCreationAgentState

rule_proposer_llm = llm.with_structured_output(ProposedRules)

propose_rules_chain = propose_rules_prompt | rule_proposer_llm

def propose_rules_node(state: RuleCreationAgentState) -> RuleCreationAgentState:
    result: ProposedRules = propose_rules_chain.invoke(
        {
            "native_language": state["native_language"],
            "target_language": state["target_language"],
        }
    )

    return {
        **state,
        "proposed_rules": [rule.model_dump() for rule in result.rules],
    }