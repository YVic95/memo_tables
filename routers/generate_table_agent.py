from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from graphs.models import GenerateTableRequest
from graphs.generate_table_graph import graph as generate_table_graph
from crud.language_pairs import get_language_pair_by_id

router = APIRouter(tags=["generate-table"])

@router.post("/api/generate-table")
def generate_tables(
    body: GenerateTableRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    result = generate_table_graph.invoke({
        "db": db,
        "grammar_rule_id": body.grammar_rule_id,
        "native_language": pair["native_name"],
        "target_language": pair["target_name"],
    })

    return {
        "general_table": result["general_table"],
        "fragmented_tables": result.get("fragmented_tables", []),
    }
