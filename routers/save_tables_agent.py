from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.language_pairs import get_language_pair_by_id
from crud.rules import get_grammar_rule_by_id
from crud.table_data import count_saved_data
from graphs.models import SaveTablesRequest, TableData
from graphs.save_table_graph import graph

router = APIRouter(tags=["save-tables"])


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"

def _validate_tables(tables: list[TableData]) -> None:
    if not tables:
        raise HTTPException(status_code=400, detail="Tables list must not be empty")

    for table in tables:
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

    fragmented = [table for table in body.tables if table.fragmented_table_id is not None]
    tables_to_save = fragmented if fragmented else [table for table in body.tables if table.fragmented_table_id is None]

    _validate_tables(tables_to_save)

    try:
        graph.invoke(
            {
                "db": db,
                "language_pair_id": body.language_pair_id,
                "session_id": str(body.session_id),
                "grammar_rule_id": body.grammar_rule_id,
                "tables": [table.model_dump() for table in tables_to_save],
                "target_language_id": None,
                "native_language_id": None,
                "word_category_slug": None,
                "base_words_to_save": [],
                "form_to_base_word_id": {},
            }
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    tables_desc = ", ".join(
        f"'{table.title}' ({_plural(len(table.rows), 'row')})" for table in tables_to_save
    )
    counts = count_saved_data(db, body.grammar_rule_id)
    message = (
        f"Saved {_plural(len(tables_to_save), 'table')}: {tables_desc}. "
        f"Stored {_plural(counts['sentences'], 'sentence')}, "
        f"{_plural(counts['word_forms'], 'word form')}, "
        f"{_plural(counts['base_words'], 'base word')}."
    )

    return {
        "status": "saved",
        "grammar_rule_id": str(body.grammar_rule_id),
        "message": message,
    }
