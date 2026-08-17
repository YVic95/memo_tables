from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.language_pairs import get_language_pair_by_id
from graphs.models import SaveTablesRequest

router = APIRouter(tags=["save-tables"])

@router.post("/api/save-tables")
def save_tables(
    body: SaveTablesRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    return {"status": "Save process initiated"}
