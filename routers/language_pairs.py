from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi import Form
from database import get_db
from crud.language_pairs import (
    get_language_pairs,
    create_language_pair,
    delete_language_pair_by_id,
)
from core.templates import templates

router = APIRouter(tags=["language-pairs"])

@router.post("/admin-panel/language-pairs")
async def save_language_pair(
    request: Request,
    native_language_id: Annotated[str, Form()],
    study_language_id: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        create_language_pair(db, native_language_id, study_language_id)
    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/_language_pair_error.html",
            context={"error": str(e)},
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/_language_pairs_list.html",
        context={"language_pairs": get_language_pairs(db)},
    )

# Delete language pair from the table
@router.delete("/admin-panel/language-pairs/{pair_id}")
async def delete_language_pair_route(
    request: Request,
    pair_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    delete_language_pair_by_id(db, pair_id)

    return templates.TemplateResponse(
        request=request,
        name="partials/_language_pairs_list.html",
        context={"language_pairs": get_language_pairs(db)},
    )

# API endpoint to get language pairs for frontend
@router.get("/api/language-pairs")
async def get_language_pairs_api(db: Annotated[Session, Depends(get_db)]):
    pairs = get_language_pairs(db)
    return JSONResponse(content={"language_pairs": pairs})