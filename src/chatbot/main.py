from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Importamos exclusivamente los componentes independientes
# (la config se lee vía pydantic-settings, que carga el .env por sí solo).
from chatbot.logging_config import configure_logging
from chatbot.mcp_client import get_mcp_client
from chatbot.mcp_host import ChatbotHost
from chatbot.routes import router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orquestador principal: levanta el cliente MCP y lo inyecta a la memoria global."""
    logger.info("🚀 Levantando todo el ecosistema de la aplicación...")

    # Obtenemos la conexión con el servidor MCP
    async with get_mcp_client() as mcp_client:
        # Inyectamos instacias listas para usarse en las rutas HTTP
        app.state.mcp_client = mcp_client
        app.state.mcp_host = ChatbotHost()
        # IDs de mensajes de WhatsApp ya procesados (dedup). Acotado en memoria:
        # Meta entrega "at least once", así que el mismo id puede llegar repetido.
        app.state.whatsapp_seen_ids = deque(maxlen=1000)
        yield


# Configuracion central del FastAPI
app = FastAPI(title="Chatbot AI Backend", lifespan=lifespan)

# 🔥 Configuración CORS para permitir peticiones desde tu frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Permitimos Vite local
    allow_credentials=True,
    allow_methods=["*"],  # Permitimos todos los metodos (GET, POST, etc)
    allow_headers=["*"],  # Permitimos cualquier header
)

app.include_router(router)


def start():
    import uvicorn

    uvicorn.run("chatbot.main:app", host="127.0.0.1", port=8000, reload=True)


def test():
    """Corre la suite de tests: `uv run test` (acepta args, ej: `uv run test -k webhook`)."""
    import sys
    import pytest

    # Reenvía cualquier argumento extra a pytest (la config vive en pyproject.toml).
    raise SystemExit(pytest.main(sys.argv[1:]))
