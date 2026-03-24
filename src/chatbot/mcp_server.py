from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server.fastmcp import FastMCP
from chatbot.database import engine

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Maneja el inicio y cierre de la conexión a la DB[cite: 368]."""
    # Aquí podrías poner un test de conexión inicial
    try:
        yield {} 
    finally:
        # Cerramos el motor de SQLAlchemy al apagar el servidor
        await engine.dispose()

# Creamos la instancia de FastMCP [cite: 368]
mcp = FastMCP(
    "Chatbot-Production",
    lifespan=app_lifespan,
    description="Servidor para consultar datos de producción y métricas"
)

# Importamos las herramientas para que el servidor las reconozca
import chatbot.tools.db_tools