from fastapi import APIRouter, Request, Depends
from core.templates import templates

router = APIRouter(prefix="/login", tags=["login"])
# Login page route
@router.get("")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )