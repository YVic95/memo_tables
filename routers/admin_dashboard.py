from fastapi import APIRouter, Request, Depends
from typing import Annotated
from routers.auth import require_admin
from core.render import render_section
from core.menu import menu_sections

router = APIRouter(prefix="/admin-panel", tags=["admin-panel"])

@router.get("")
async def admin_panel(request: Request, user: Annotated[dict, Depends(require_admin)]):
    return render_section(
        request = request,
        full_template="admin-panel.html",
        fragment_template="menu-sections/_dashboard_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
        },
    )