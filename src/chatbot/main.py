from fastapi import FastAPI
import uvicorn

app = FastAPI(title="LexiFly AI Backend")

@app.get("/")
async def health_check():
    return {
        "status": "online",
        "service": "LexiFly-MCP",
        "version": "0.1.0"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)