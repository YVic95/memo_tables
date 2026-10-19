import uuid
from fastapi import APIRouter, Depends, Request
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import require_admin
from core.render import render_section
from core.templates import templates
from core.menu import menu_sections
from graphs.prompts import correction_prompt
from crud.canonical_rules import get_all_canonical_rules_for_pair
from crud.language_pairs import get_language_pair_by_id, get_language_pairs

router = APIRouter(prefix="/admin-panel/canonical-rules", tags=["canonical-rules"])

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
    rules = []
    if pair is not None:
        rules = get_all_canonical_rules_for_pair(
            db,
            native_language_id=pair["native_language_id"],
            target_language_id=pair["target_language_id"],
        )
    return templates.TemplateResponse(
        request=request,
        name="partials/_canonical_rules_list.html",
        context={"pair": pair, "rules": rules},
    )
