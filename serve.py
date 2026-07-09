from fastapi import FastAPI, Request, Depends, Form, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse
from routers.auth import router as auth_router
from routers.languages import router as languages_router
from routers.admin_dashboard import router as admin_dashboard_router
from routers.language_pairs import router as language_pairs_router
from routers.grammar_rules import router as grammar_rules_router
from routers.legal_pages import router as legal_pages_router
from routers.user_login import router as user_login_router
from routers.create_rule_agent import router as create_rule_agent_router

load_dotenv()

app = FastAPI(
    title="Memo Tables App",
    version="1.0",
    description="App for learning a language using memo tables"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(languages_router)
app.include_router(admin_dashboard_router)
app.include_router(language_pairs_router)
app.include_router(grammar_rules_router)
app.include_router(legal_pages_router)
app.include_router(user_login_router)
app.include_router(create_rule_agent_router)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)