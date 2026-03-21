from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Chatbot AI Backend")

@app.get("/")
async def health_check():
    return {
        "status": "online",
        "service": "chatbot-MCP",
        "version": "0.1.0"
    }

def start():
    """Lanzado con `poetry run start` a través del script en pyproject.toml"""
    uvicorn.run("chatbot.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    start()