import uuid
from fastapi import APIRouter, Depends, Form, Request
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import require_admin
from core.render import render_section
from core.templates import templates
from core.menu import menu_sections
from graphs.prompts import correction_prompt
from crud.canonical_rules import (
    CEFR_LEVELS,
    create_canonical_rule,
    get_all_canonical_rules_for_pair,
)
from crud.language_pairs import get_language_pair_by_id, get_language_pairs
from crud.rules import get_word_categories

router = APIRouter(prefix="/admin-panel/canonical-rules", tags=["canonical-rules"])
RULES_LIST_LOCATION = "partials/_canonical_rules_list.html"

def _rules_list_context(db: Session, pair: dict) -> dict:
    return {
        "pair": pair,
        "rules": get_all_canonical_rules_for_pair(
            db,
            native_language_id=pair["native_language_id"],
            target_language_id=pair["target_language_id"],
        ),
    }

def _form_error_response(request: Request, message: str):
    return templates.TemplateResponse(
        request=request,
        name="partials/_canonical_rule_error.html",
        context={"error": message},
        status_code=400,
        headers={
            "HX-Retarget": "#canonical-rule-form-error",
            "HX-Reswap": "innerHTML",
        },
    )

@router.get("")
async def canonical_rules_section(
    request: Request,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return render_section(
        request=request,
        full_template="admin-panel-canonical-rules.html",
        fragment_template="menu-sections/_canonical_rules_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
            "correction_prompt": correction_prompt,
            "language_pairs": get_language_pairs(db),
            "word_categories": get_word_categories(db),
            "cefr_levels": CEFR_LEVELS,
        },
    )

@router.get("/rules")
async def canonical_rules_list(
    request: Request,
    pair_id: uuid.UUID,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, pair_id)
    if pair is None:
        return templates.TemplateResponse(
            request=request,
            name=RULES_LIST_LOCATION,
            context={"pair": None, "rules": []},
        )
    return templates.TemplateResponse(
        request=request,
        name=RULES_LIST_LOCATION,
        context=_rules_list_context(db, pair),
    )

@router.post("/rules")
async def create_canonical_rule_route(
    request: Request,
    word_category_id: Annotated[uuid.UUID, Form()],
    level: Annotated[str, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    slug: Annotated[str, Form()],
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    pair_id: Annotated[str, Form()] = "",
):
    try:
        pair_uuid = uuid.UUID(pair_id)
    except ValueError:
        return _form_error_response(request, "Select a language pair.")

    pair = get_language_pair_by_id(db, pair_uuid)
    if pair is None:
        return _form_error_response(request, "Language pair not found.")

    try:
        create_canonical_rule(
            db,
            native_language_id=pair["native_language_id"],
            target_language_id=pair["target_language_id"],
            word_category_id=word_category_id,
            level=level,
            name=name,
            description=description,
            slug=slug,
        )
    except ValueError as e:
        return _form_error_response(request, str(e))

    return templates.TemplateResponse(
        request=request,
        name=RULES_LIST_LOCATION,
        context=_rules_list_context(db, pair),
    )
