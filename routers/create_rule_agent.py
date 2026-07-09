from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
from pydantic import BaseModel
from database import get_db
from crud.language_pairs import get_language_pair_by_id

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

    # placeholder response until the actual agent logic is wired in
    return {
        "text": f"Received request type '{body.type}' for pair {pair['native_name']} → {pair['target_name']}"
    }