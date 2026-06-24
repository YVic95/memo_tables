from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from routers.auth import require_admin
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse
import os

load_dotenv()

from routers.auth import router as auth_router

app = FastAPI(
    title="Memo Tables App",
    version="1.0",
    description="App for learning a language using memo tables"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)

@app.get("/privacy")
async def privacy_policy():
    return FileResponse(os.path.join(os.path.dirname(__file__), "docs/privacy_policy.md"), media_type="text/plain")


@app.get("/terms")
async def terms_of_service():
    return FileResponse(os.path.join(os.path.dirname(__file__), "docs/terms_of_service.md"), media_type="text/plain")

# test
from typing import Annotated
from fastapi import Depends
from routers.auth import get_current_user

@app.get("/me")
def me(user: Annotated[dict, Depends(get_current_user)]):
    return user
# test

# Login page route
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )

# Helper function for rendering the content of different pages from the admin
def render_section(
    request: Request,
    full_template: str,
    fragment_template: str,
    context: dict,
):
    """
    Render an admin-panel section.

    - Direct navigation / refresh / bookmark -> full page (layout + content)
    - htmx nav click (HX-Request header present) -> the content fragment
      that gets swapped into #main-content
    """
    is_htmx = request.headers.get("HX-Request") == "true"
    return templates.TemplateResponse(
        request=request,
        name=fragment_template if is_htmx else full_template,
        context=context,
    )


# Main admin page
menu_sections = [
    {"label": "Dashboard", "url": "/admin-panel"},
    {"label": "Languages", "url": "/admin-panel/languages"},
    # {"label": "Rules", "url": "/admin-panel/rules"},
    # {"label": "Words", "url": "/admin-panel/words"},
    # {"label": "Exercises", "url": "/admin-panel/exercises"},
]

@app.get("/admin-panel")
async def admin_panel(request: Request, user: Annotated[dict, Depends(require_admin)]):
    return render_section(
        request,
        full_template="admin-panel.html",
        fragment_template="menu-sections/_dashboard_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
        },
    )

@app.get("/admin-panel/languages")
async def languages_section(request: Request, user: Annotated[dict, Depends(require_admin)]):
    return render_section(
        request,
        full_template="admin-panel-languages.html",
        fragment_template="menu-sections/_languages_content.html",
        context={
            "user": user,
            "menu_sections": menu_sections,
            # "languages": await get_languages(),  # data fetch from the "available_languages" DB table 
        },
    )

# redirect to the login if cookie is expired
@app.exception_handler(FastAPIHTTPException)
async def redirect_unauthenticated(request: Request, exc: FastAPIHTTPException):
    if exc.status_code in (401, 403) and not request.url.path.startswith("/auth"):
        return RedirectResponse(url="/login")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

@app.get("/")
async def root():
    return {"message": "Welcome to the Memo Tables App!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)