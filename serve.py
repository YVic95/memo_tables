from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
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

@app.get("/")
async def root():
    return {"message": "Welcome to the Memo Tables App!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)