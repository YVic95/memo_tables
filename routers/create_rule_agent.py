import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated, TypedDict
from pydantic import BaseModel, Field
from database import get_db
from crud.language_pairs import get_language_pair_by_id
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from langchain_core.prompts import PromptTemplate

load_dotenv()
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

router = APIRouter(tags=["create-rule-agent"])

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

propose_rules_prompt = PromptTemplate.from_template(
    """
        You are a language-learning content expert.
        Suggest exactly 5 fundamental grammar or usage rules a native
        {native_language} speaker should learn first when studying
        {target_language}.
        Keep explanations concise and beginner-friendly.
        Rules should be written in the {native_language} of user!
    """
)

# --- Structured output schema for the LLM ---
class Rule(BaseModel):
    title: str = Field(description="Short name of the grammar/language rule")
    explanation: str = Field(description="Clear explanation of the rule, written in the native language of the user about the target language")

class ProposedRules(BaseModel):
    rules: list[Rule] = Field(description="Exactly 5 proposed rules in users language")

rule_proposer_llm = llm.with_structured_output(ProposedRules)

# --- Graph state ---
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

# --- Graph ---
graph_builder = StateGraph(RuleCreationAgentState)
graph_builder.add_node("propose_rules", propose_rules_node)
graph_builder.add_edge(START, "propose_rules")
graph_builder.add_edge("propose_rules", END)
rule_agent_graph = graph_builder.compile()

# --- API schema ---
class AgentRequest(BaseModel):
    type: str
    language_pair_id: str

@router.post("/api/create-rule-agent")
async def call_agent(
    body: AgentRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    if body.type != "propose_missing_rules":
        raise HTTPException(status_code=400, detail=f"Unsupported request type: {body.type}")

    result = rule_agent_graph.invoke({
        "native_language": pair["native_name"],
        "target_language": pair["target_name"],
        "proposed_rules": [],
    })

    return {"rules": result["proposed_rules"]}