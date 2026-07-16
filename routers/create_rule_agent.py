from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from crud.language_pairs import get_language_pair_by_id
from graphs.suggest_rules_graph import graph as propose_rules_graph
from graphs.initial_rule_graph import graph as initial_rule_graph

router = APIRouter(tags=["create-rule-agent"])

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
    
    if body.type == "propose_missing_rules":
        result = propose_rules_graph.invoke({
            "native_language": pair["native_name"],
            "target_language": pair["target_name"],
            "proposed_rules": [],
        })
        return {"rules": result["proposed_rules"]}
    
    if body.type == "initial_rule":
        if not body.title or not body.explanation:
            raise HTTPException(status_code=400, detail="title and explanation are required")

        result = initial_rule_graph.invoke({
            "db": db,
            "rule_title": body.title,
            "rule_explanation": body.explanation,
            "native_language": pair["native_name"],
            "target_language": pair["target_name"],
            "native_language_id": pair["native_language_id"],
            "target_language_id": pair["target_language_id"],
        })

        return {
            "grammar_rule_id": result["grammar_rule_id"],
            "full_content": result["full_content"],
        }
    else:
        raise HTTPException(
                status_code=400,
                detail=f"Unsupported request type: {body.type}",
            )
