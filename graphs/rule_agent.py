import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from graphs.llm import llm
from graphs.prompts import propose_rules_prompt
from graphs.models import ProposedRules
from graphs.states import RuleCreationAgentState

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

rule_proposer_llm = llm.with_structured_output(ProposedRules)

def propose_rules_node(state: RuleCreationAgentState) -> RuleCreationAgentState:
    prompt = propose_rules_prompt.format(
        native_language=state["native_language"],
        target_language=state["target_language"],
    )

    result: ProposedRules = rule_proposer_llm.invoke(prompt)

    return {
        **state,
        "proposed_rules": [rule.model_dump() for rule in result.rules],
    }

graph_builder = StateGraph(RuleCreationAgentState)

graph_builder.add_node("propose_rules", propose_rules_node)
graph_builder.add_edge(START, "propose_rules")
graph_builder.add_edge("propose_rules", END)

graph = graph_builder.compile()