import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from graphs.llm import llm

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

propose_rules_prompt = PromptTemplate.from_template(
    """
You are a language-learning content expert.

Suggest exactly 5 fundamental grammar or usage rules a native
{native_language} speaker should learn first when studying
{target_language}.

Keep explanations concise and beginner-friendly.

Rules should be written in the {native_language} of the user.
"""
)


class Rule(BaseModel):
    title: str = Field(description="Short name of the grammar/language rule")
    explanation: str = Field(
        description="""
Clear explanation of the rule, written in the user's native language.
Keep it short and explain why the learner should know this rule.
"""
    )


class ProposedRules(BaseModel):
    rules: list[Rule] = Field(description="Exactly 5 proposed rules")


rule_proposer_llm = llm.with_structured_output(ProposedRules)


class RuleCreationAgentState(TypedDict):
    native_language: str
    target_language: str
    proposed_rules: list[dict]


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