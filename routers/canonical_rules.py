import uuid
from fastapi import APIRouter, Depends, Form, Request
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import require_admin
from core.render import render_section
from core.templates import templates
from core.menu import menu_sections
from crud.canonical_rules import (
    CEFR_LEVELS,
    create_canonical_rule,
    get_all_canonical_rules_for_pair,
    get_canonical_rule_by_id,
    update_canonical_rule,
)
from crud.language_pairs import get_language_pair_by_id, get_language_pairs
from crud.rules import get_word_categories
from models.canonical_rules import CanonicalRule

router = APIRouter(prefix="/admin-panel/canonical-rules", tags=["canonical-rules"])
RULES_LIST_LOCATION = "partials/_canonical_rules_list.html"
RULE_EDIT_MODAL_LOCATION = "partials/_canonical_rule_edit_modal.html"
RULE_ERROR_LOCATION = "partials/_canonical_rule_error.html"
RULE_FORM_ERROR_TARGET = "#canonical-rule-form-error"
RULE_EDIT_ERROR_TARGET = "#canonical-rule-edit-error"

def _rule_form_context(
    db: Session, rule: CanonicalRule | None = None
) -> dict:
    return {
        "rule": rule,
        "word_categories": get_word_categories(db),
        "cefr_levels": CEFR_LEVELS,
    }

def _rules_list_context(db: Session, pair: dict) -> dict:
    return {
        "pair": pair,
        "rules": get_all_canonical_rules_for_pair(
            db,
            native_language_id=pair["native_language_id"],
            target_language_id=pair["target_language_id"],
        ),
    }

def _form_error_response(request: Request, message: str, target: str):
    return templates.TemplateResponse(
        request=request,
        name=RULE_ERROR_LOCATION,
        context={"error": message},
        status_code=400,
        headers={
            "HX-Retarget": target,
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
            "language_pairs": get_language_pairs(db),
            **_rule_form_context(db),
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

@router.patch("/rules/{rule_id}")
async def update_canonical_rule_route(
    request: Request,
    rule_id: uuid.UUID,
    word_category_id: Annotated[uuid.UUID, Form()],
    level: Annotated[str, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    slug: Annotated[str, Form()],
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        rule = update_canonical_rule(
            db,
            rule_id=rule_id,
            word_category_id=word_category_id,
            level=level,
            name=name,
            description=description,
            slug=slug,
        )
    except ValueError as e:
        return _form_error_response(request, str(e), RULE_EDIT_ERROR_TARGET)

    if rule is None:
        return _form_error_response(request, "Rule not found.", RULE_EDIT_ERROR_TARGET)

    # Re-render the rule's own pair list; the rule carries that pair's ids.
    pair = {
        "native_language_id": rule.native_language_id,
        "target_language_id": rule.target_language_id,
    }

    return templates.TemplateResponse(
        request=request,
        name=RULES_LIST_LOCATION,
        context=_rules_list_context(db, pair),
    )

@router.get("/rules/{rule_id}/edit")
async def edit_canonical_rule_form(
    request: Request,
    rule_id: uuid.UUID,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    rule = get_canonical_rule_by_id(db, rule_id)
    if rule is None:
        return templates.TemplateResponse(
            request=request,
            name=RULE_ERROR_LOCATION,
            context={"error": "Rule not found."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request=request,
        name=RULE_EDIT_MODAL_LOCATION,
        context=_rule_form_context(db, rule),
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
        return _form_error_response(request, "Select a language pair.", RULE_FORM_ERROR_TARGET)

    pair = get_language_pair_by_id(db, pair_uuid)
    if pair is None:
        return _form_error_response(request, "Language pair not found.", RULE_FORM_ERROR_TARGET)

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
        return _form_error_response(request, str(e), RULE_FORM_ERROR_TARGET)

    return templates.TemplateResponse(
        request=request,
        name=RULES_LIST_LOCATION,
        context=_rules_list_context(db, pair),
    )
