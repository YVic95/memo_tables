from fastapi import APIRouter, Request, Depends
from typing import Annotated
from routers.auth import require_admin
from core.render import render_section
from core.menu import menu_sections
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter(prefix="/admin-panel/rules", tags=["rules"])

# Page for rule creation
@router.get("")
async def rules_section(
    request: Request,
    user: Annotated[dict, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return render_section(
        request = request,
        full_template="admin-panel-rules.html",
        fragment_template="menu-sections/_rules_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
        },
    )