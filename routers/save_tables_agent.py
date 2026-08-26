from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.language_pairs import get_language_pair_by_id
from crud.rules import get_grammar_rule_by_id
from graphs.models import SaveTablesRequest

router = APIRouter(tags=["save-tables"])

def _validate_save_tables_request(body: SaveTablesRequest) -> None:
    if not body.tables:
        raise HTTPException(status_code=400, detail="Tables list must not be empty")

    for table in body.tables:
        if not table.rows:
            raise HTTPException(status_code=400, detail=f"Table '{table.title}' must have at least one row")

        for i, row in enumerate(table.rows):
            if len(row.cells) != len(table.headers):
                raise HTTPException(
                    status_code=400,
                    detail=f"Row {i + 1} in table '{table.title}' has {len(row.cells)} cells but headers have {len(table.headers)} columns",
                )

@router.post("/api/save-tables")
def save_tables(
    body: SaveTablesRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    rule = get_grammar_rule_by_id(db, body.grammar_rule_id)
    if rule is None:
        raise HTTPException(status_code=400, detail="Grammar rule not found")

    _validate_save_tables_request(body)

    return {"status": "Save process initiated", "grammar_rule_id": body.grammar_rule_id}
