from fastapi import FastAPI, Request, Depends, Form, Response
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from routers.auth import require_admin, get_current_user
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from crud.languages import get_languages, create_language
from crud.language_pairs import get_language_pairs, create_language_pair, delete_language_pair_by_id
from typing import Annotated
from country_flags import get_flag
import os

load_dotenv()

from routers.auth import router as auth_router
from routers.languages import router as languages_router
from routers.admin_dashboard import router as admin_dashboard_router

app = FastAPI(
    title="Memo Tables App",
    version="1.0",
    description="App for learning a language using memo tables"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.filters["flag"] = get_flag

app.include_router(auth_router)
app.include_router(languages_router)
app.include_router(admin_dashboard_router)

@app.get("/privacy")
async def privacy_policy():
    return FileResponse(os.path.join(os.path.dirname(__file__), "docs/privacy_policy.md"), media_type="text/plain")


@app.get("/terms")
async def terms_of_service():
    return FileResponse(os.path.join(os.path.dirname(__file__), "docs/terms_of_service.md"), media_type="text/plain")

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
    {"label": "Dashboard", "url": "/admin-panel", "logo": "fa-table-cells-large"},
    {"label": "Languages", "url": "/admin-panel/languages", "logo": "fa-book-atlas"},
    {"label": "Rule Creation", "url": "/admin-panel/rules", "logo": "fa-gear"},
    # {"label": "Words", "url": "/admin-panel/words"},
    # {"label": "Exercises", "url": "/admin-panel/exercises"},
]

@app.post("/admin-panel/language-pairs")
async def save_language_pair(
    request: Request,
    native_language_id: Annotated[str, Form()],
    study_language_id: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        create_language_pair(
            db,
            native_language_id,
            study_language_id,
        )

    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/_language_pair_error.html",
            context={
                "error": str(e),
            },
            status_code=400,
        )

    pairs = get_language_pairs(db)

    return templates.TemplateResponse(
        request=request,
        name="partials/_language_pairs_list.html",
        context={
            "language_pairs": pairs,
        },
    )

# Delete language pair from the table
@app.delete("/admin-panel/language-pairs/{pair_id}")
async def delete_language_pair_route(
    request: Request,
    pair_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    delete_language_pair_by_id(db, pair_id)

    pairs = get_language_pairs(db)

    return templates.TemplateResponse(
        request=request,
        name="partials/_language_pairs_list.html",
        context={
            "language_pairs": pairs,
        },
    )

# Page for rule creation
@app.get("/admin-panel/rules")
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

# API endpoint to get language pairs for frontend
@app.get("/api/language-pairs")
async def get_language_pairs_api(db: Annotated[Session, Depends(get_db)]):
    pairs = get_language_pairs(db)
    return JSONResponse(content={"language_pairs": pairs})

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