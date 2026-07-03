"""Cliente de embeddings: convierte texto en vectores usando OpenAI.

Claude no tiene una API de embeddings propia. Para RAG usamos OpenAI
unicamente para este paso puntual (texto -> vector); el resto del pipeline
(chunking, busqueda, respuesta final) no depende de OpenAI.
"""

from openai import AsyncOpenAI

from chatbot.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_text(text: str) -> list[float]:
    """Devuelve el vector de embedding de un unico texto (ej: la pregunta del usuario)."""
    response = await _client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Devuelve un vector por cada texto de la lista, en el mismo orden (ingesta)."""
    response = await _client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
