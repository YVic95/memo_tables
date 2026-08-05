from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from graphs.models import TableData
from graphs.edit_tables_graph import graph as edit_tables_graph
from crud.language_pairs import get_language_pair_by_id

router = APIRouter(tags=["edit-tables"])


class EditTableRequest(BaseModel):
    language_pair_id: str
    instructions: str
    table: TableData


@router.post("/api/edit-tables")
def edit_tables(
    body: EditTableRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    print("[edit-tables] language_pair_id:", body.language_pair_id)
    print("[edit-tables] instructions:", body.instructions)

    result = edit_tables_graph.invoke({
        "native_language": pair["native_name"],
        "target_language": pair["target_name"],
        "instructions": body.instructions,
        "table": body.table.model_dump(),
    })

    return {"edited_table": result["edited_table"]}