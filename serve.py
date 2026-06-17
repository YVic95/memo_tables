from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI(
    title="Memo Tables App",
    version="1.0",
    description="App for learning a language using memo tables"
)

@app.get("/privacy")
async def privacy_policy():
    return FileResponse(os.path.join(os.path.dirname(__file__), "docs/privacy_policy.md"), media_type="text/plain")


@app.get("/terms")
async def terms_of_service():
    return FileResponse(os.path.join(os.path.dirname(__file__), "docs/terms_of_service.md"), media_type="text/plain")


@app.get("/")
async def root():
    return {"message": "Welcome to the Memo Tables App!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)