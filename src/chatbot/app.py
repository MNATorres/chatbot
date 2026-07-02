from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from chatbot.database import engine


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Maneja el inicio y cierre de la base de datos."""
    # Aquí podrías poner un print("Conectado!")
    try:
        yield
    finally:
        # Esto asegura que al cerrar el inspector, se libere MySQL
        await engine.dispose()


# PASO CLAVE: El lifespan se pasa como argumento aquí
mcp = FastMCP(
    "Chatbot-Production", instructions="Servidor para consultar datos de producción y métricas", lifespan=app_lifespan
)
