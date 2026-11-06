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
    get_canonical_rule_categories_for_pair,
    resolve_canonical_category_name,
    get_linked_canonical_rule_ids,
    set_canonical_rule_active,
    update_canonical_rule,
)
from crud.language_pairs import get_language_pair_by_id, get_language_pairs
from crud.rules import get_word_categories
from models.canonical_rules import CanonicalRule

router = APIRouter(prefix="/admin-panel/canonical-rules", tags=["canonical-rules"])
RULES_LIST_LOCATION = "partials/_canonical_rules_list.html"
RULES_PANEL_LOCATION = "partials/_canonical_rules_panel.html"
RULE_EDIT_MODAL_LOCATION = "partials/_canonical_rule_edit_modal.html"
RULE_ERROR_LOCATION = "partials/_canonical_rule_error.html"
RULE_FORM_ERROR_TARGET = "#canonical-rule-form-error"
RULE_EDIT_ERROR_TARGET = "#canonical-rule-edit-error"
RULE_NOT_FOUND = "Rule not found."
EMPTY_FILTERS = {"level": "", "category": "", "status": ""}

FILTER_VALS_JS = (
    "js:{filter_level: document.getElementById('catalogue-filter-level').value, "
    "filter_category: document.getElementById('catalogue-filter-category').value, "
    "filter_status: document.getElementById('catalogue-filter-status').value, "
    "filter_sort: document.getElementById('catalogue-sort').value, "
    "filter_dir: document.getElementById('catalogue-dir').value}"
)

def _rule_form_context(
    db: Session, rule: CanonicalRule | None = None
) -> dict:
    return {
        "rule": rule,
        "word_categories": get_word_categories(db),
        "cefr_levels": CEFR_LEVELS,
        "filter_vals_js": FILTER_VALS_JS,
    }

def _rules_list_context(
    db: Session,
    pair: dict,
    *,
    level: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sort: str | None = None,
    direction: str | None = None,
) -> dict:
    rules = get_all_canonical_rules_for_pair(
        db,
        native_language_id=pair["native_language_id"],
        target_language_id=pair["target_language_id"],
        level=level,
        category=category,
        status=status,
        sort=sort,
        direction=direction,
    )
    rule_ids = [rule["id"] for rule in rules]
    linked_ids = get_linked_canonical_rule_ids(db, rule_ids)
    for rule in rules:
        rule["is_linked"] = rule["id"] in linked_ids
    return {
        "pair": pair,
        "rules": rules,
        "filters": dict(
            EMPTY_FILTERS, level=level or "", category=category or "", status=status or ""
        ),
        "sort": sort or "",
        "dir": direction or "",
    }

def _resolve_language_pair(db: Session, pair_id: str) -> dict | None:
    if not pair_id:
        return None
    try:
        pair_uuid = uuid.UUID(pair_id)
    except ValueError:
        return None
    return get_language_pair_by_id(db, pair_uuid)


def _pair_context(
    db: Session,
    pair_id: str,
    *,
    level: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sort: str | None = None,
    direction: str | None = None,
) -> dict:
    """The pair the section is scoped to, together with that pair's rules."""
    pair = _resolve_language_pair(db, pair_id)
    if pair is None:
        return {
            "pair": None,
            "rules": None,
            "filter_categories": [],
            "filters": dict(EMPTY_FILTERS),
            "sort": "",
            "dir": "",
        }
    filter_categories = get_canonical_rule_categories_for_pair(
        db,
        native_language_id=pair["native_language_id"],
        target_language_id=pair["target_language_id"],
    )
    if category:
        category = resolve_canonical_category_name(
            db,
            native_language_id=pair["native_language_id"],
            target_language_id=pair["target_language_id"],
            value=category,
        )
    return {
        **_rules_list_context(
            db,
            pair,
            level=level,
            category=category,
            status=status,
            sort=sort,
            direction=direction,
        ),
        "filter_categories": filter_categories,
    }


def _catalogue_context(
    db: Session,
    pair_id: str,
    *,
    level: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sort: str | None = None,
    direction: str | None = None,
) -> dict:
    """Everything the catalogue panel renders, including the create-form choices."""
    pair_context = _pair_context(
        db,
        pair_id,
        level=level,
        category=category,
        status=status,
        sort=sort,
        direction=direction,
    )
    if pair_context["pair"] is None:
        return pair_context
    return {**pair_context, **_rule_form_context(db)}


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
    pair_id: str = "",
    level: str = "",
    category: str = "",
    status: str = "",
    sort: str = "",
    dir: str = "",
):
    return render_section(
        request=request,
        full_template="admin-panel-canonical-rules.html",
        fragment_template="menu-sections/_canonical_rules_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
            "language_pairs": get_language_pairs(db),
            **_catalogue_context(
                db,
                pair_id,
                level=level or None,
                category=category or None,
                status=status or None,
                sort=sort or None,
                direction=dir or None,
            ),
        },
    )

@router.get("/panel")
async def canonical_rules_panel(
    request: Request,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    pair_id: str = "",
    level: str = "",
    category: str = "",
    status: str = "",
    sort: str = "",
    dir: str = "",
):
    return templates.TemplateResponse(
        request=request,
        name=RULES_PANEL_LOCATION,
        context=_catalogue_context(
            db,
            pair_id,
            level=level or None,
            category=category or None,
            status=status or None,
            sort=sort or None,
            direction=dir or None,
        ),
    )


@router.get("/rules")
async def canonical_rules_list(
    request: Request,
    pair_id: uuid.UUID,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    level: str = "",
    category: str = "",
    status: str = "",
    sort: str = "",
    dir: str = "",
):
    pair = get_language_pair_by_id(db, pair_id)
    if pair is None:
        return templates.TemplateResponse(
            request=request,
            name=RULES_LIST_LOCATION,
            context={
                "pair": None,
                "rules": [],
                "filters": dict(EMPTY_FILTERS),
                "sort": "",
                "dir": "",
            },
        )
    return templates.TemplateResponse(
        request=request,
        name=RULES_LIST_LOCATION,
        context=_rules_list_context(
            db,
            pair,
            level=level or None,
            category=category or None,
            status=status or None,
            sort=sort or None,
            direction=dir or None,
        ),
    )


def _rule_not_found_response(request: Request):
    return templates.TemplateResponse(
        request=request,
        name=RULE_ERROR_LOCATION,
        context={"error": RULE_NOT_FOUND},
        status_code=404,
    )


def _rules_list_response(
    request: Request,
    db: Session,
    rule,
    *,
    level: str = "",
    category: str = "",
    status: str = "",
    sort: str = "",
    direction: str = "",
):
    """Re-render the rules list for the language pair this rule belongs to."""
    pair = {
        "native_language_id": rule.native_language_id,
        "target_language_id": rule.target_language_id,
    }
    return templates.TemplateResponse(
        request=request,
        name=RULES_LIST_LOCATION,
        context=_rules_list_context(
            db,
            pair,
            level=level or None,
            category=category or None,
            status=status or None,
            sort=sort or None,
            direction=direction or None,
        ),
    )


def _set_rule_active_response(
    request: Request,
    db: Session,
    rule_id: uuid.UUID,
    active: bool,
    *,
    level: str = "",
    category: str = "",
    status: str = "",
    sort: str = "",
    direction: str = "",
):
    rule = set_canonical_rule_active(db, rule_id, active)
    if rule is None:
        return _rule_not_found_response(request)
    return _rules_list_response(
        request,
        db,
        rule,
        level=level,
        category=category,
        status=status,
        sort=sort,
        direction=direction,
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
        return _rule_not_found_response(request)
    return templates.TemplateResponse(
        request=request,
        name=RULE_EDIT_MODAL_LOCATION,
        context=_rule_form_context(db, rule),
    )


@router.post("/rules/{rule_id}")
async def update_canonical_rule_route(
    request: Request,
    rule_id: uuid.UUID,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    word_category_id: Annotated[str | None, Form()] = None,
    level: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    slug: Annotated[str | None, Form()] = None,
    filter_level: Annotated[str, Form()] = "",
    filter_category: Annotated[str, Form()] = "",
    filter_status: Annotated[str, Form()] = "",
    filter_sort: Annotated[str, Form()] = "",
    filter_dir: Annotated[str, Form()] = "",
):
    def error(message: str):
        return _form_error_response(request, message, RULE_EDIT_ERROR_TARGET)

    if None in (word_category_id, level, name, description, slug):
        return error("Missing required fields.")

    try:
        category_id = uuid.UUID(word_category_id)
    except ValueError:
        return error("Invalid word category.")

    try:
        rule = update_canonical_rule(
            db,
            rule_id=rule_id,
            word_category_id=category_id,
            level=level,
            name=name,
            description=description,
            slug=slug,
        )
    except ValueError as e:
        return error(str(e))

    if rule is None:
        return error(RULE_NOT_FOUND)
    return _rules_list_response(
        request,
        db,
        rule,
        level=filter_level,
        category=filter_category,
        status=filter_status,
        sort=filter_sort,
        direction=filter_dir,
    )


@router.post("/rules/{rule_id}/activate")
async def activate_canonical_rule_route(
    request: Request,
    rule_id: uuid.UUID,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    level: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "",
    sort: Annotated[str, Form()] = "",
    dir: Annotated[str, Form()] = "",
):
    return _set_rule_active_response(
        request,
        db,
        rule_id,
        True,
        level=level,
        category=category,
        status=status,
        sort=sort,
        direction=dir,
    )


@router.post("/rules/{rule_id}/deactivate")
async def deactivate_canonical_rule_route(
    request: Request,
    rule_id: uuid.UUID,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    level: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "",
    sort: Annotated[str, Form()] = "",
    dir: Annotated[str, Form()] = "",
):
    return _set_rule_active_response(
        request,
        db,
        rule_id,
        False,
        level=level,
        category=category,
        status=status,
        sort=sort,
        direction=dir,
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
    filter_level: Annotated[str, Form()] = "",
    filter_category: Annotated[str, Form()] = "",
    filter_status: Annotated[str, Form()] = "",
    filter_sort: Annotated[str, Form()] = "",
    filter_dir: Annotated[str, Form()] = "",
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
        context=_rules_list_context(
            db,
            pair,
            level=filter_level or None,
            category=filter_category or None,
            status=filter_status or None,
            sort=filter_sort or None,
            direction=filter_dir or None,
        ),
    )
