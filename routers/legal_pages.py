import os
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["legal"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")

@router.get("/privacy")
async def privacy_policy():
    return FileResponse(
        os.path.join(DOCS_DIR, "privacy_policy.md"),
        media_type="text/plain",
    )

@router.get("/terms")
async def terms_of_service():
    return FileResponse(
        os.path.join(DOCS_DIR, "terms_of_service.md"),
        media_type="text/plain",
    )