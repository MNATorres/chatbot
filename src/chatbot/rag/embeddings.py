"""Cliente de embeddings: convierte texto en vectores usando OpenAI.

Claude no tiene una API de embeddings propia. Para RAG usamos OpenAI
unicamente para este paso puntual (texto -> vector); el resto del pipeline
(chunking, busqueda, respuesta final) no depende de OpenAI.
"""

from openai import AsyncOpenAI

from chatbot.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Crea el cliente recien en el primer uso real, no al importar el modulo.

    Si se construyera a nivel de modulo, el servidor MCP fallaria al arrancar
    en cualquier instalacion sin OPENAI_API_KEY configurada (RAG es opcional),
    aunque nunca se llegue a usar la tool de busqueda.
    """
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def embed_text(text: str) -> list[float]:
    """Devuelve el vector de embedding de un unico texto (ej: la pregunta del usuario)."""
    response = await _get_client().embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Devuelve un vector por cada texto de la lista, en el mismo orden (ingesta)."""
    response = await _get_client().embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
