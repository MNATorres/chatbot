# src/chatbot/tools/rag_tools.py
from chatbot.app import mcp
from chatbot.rag.embeddings import embed_text
from chatbot.rag.store import search


@mcp.tool()
async def search_knowledge_base(query: str) -> str:
    """Busca en la base de conocimiento interna (normativas, reglas, instructivos)
    los fragmentos mas relevantes para responder `query`."""
    query_vector = await embed_text(query)
    chunks = search(query_vector, top_k=3)

    if not chunks:
        return "No hay documentos indexados todavia. Corre la ingesta antes de consultar."

    return "\n\n---\n\n".join(chunks)
