from fastapi import FastAPI

app = FastAPI(
    title="Memo Tables App",
    version="1.0",
    description="App for learning a language using memo tables"
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Memo Tables App!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)