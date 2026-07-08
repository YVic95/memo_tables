from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Annotated
from database import get_db
from routers.auth import require_admin
from crud.languages import get_languages, create_language
from crud.language_pairs import get_language_pairs, create_language_pair, delete_language_pair_by_id
from core.render import render_section
from core.templates import templates
from core.menu import menu_sections

router = APIRouter(prefix="/admin-panel/languages", tags=["languages"])

@router.get("")
async def languages_section(
    request: Request,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return render_section(
        request=request,
        full_template="admin-panel-languages.html",
        fragment_template="menu-sections/_languages_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
            "languages": get_languages(db),
            "language_pairs": get_language_pairs(db),
        },
    )

@router.post("/create")
async def add_language(
    request: Request,
    name: Annotated[str, Form()],
    target: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        new_language = create_language(db, name)
    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/_add_language_error.html",
            context={"error": str(e)},
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/_language_options.html",
        context={
            "languages": get_languages(db),
            "new_id": new_language["id"],
            "target": target,
        },
    )

@router.get("/modal")
async def add_language_modal(request: Request, target: str):
    return templates.TemplateResponse(
        request=request,
        name="partials/_add_language_modal.html",
        context={"target": target},
    )