"""Script de ingesta: lee los documentos de `knowledge/`, los parte en chunks,
genera un embedding por chunk y guarda el indice que despues usa la tool RAG.

Se corre a mano cada vez que agregas o cambias un documento fuente:

    uv run python -m chatbot.rag.ingest

Requiere OPENAI_API_KEY configurada en el .env (ver config.py).
"""

import asyncio
from pathlib import Path

from loguru import logger

from chatbot.config import settings
from chatbot.rag.chunking import chunk_text
from chatbot.rag.embeddings import embed_texts
from chatbot.rag.store import save_index


async def _run() -> None:
    knowledge_dir = Path(settings.RAG_KNOWLEDGE_DIR)
    documents = sorted(knowledge_dir.glob("*.md"))

    if not documents:
        logger.warning(f"No hay documentos .md en {knowledge_dir}/")
        return

    all_chunks: list[str] = []
    for doc_path in documents:
        text = doc_path.read_text(encoding="utf-8")
        doc_chunks = chunk_text(text)
        logger.info(f"Documento {doc_path.name}: {len(doc_chunks)} chunks")
        all_chunks.extend(doc_chunks)

    logger.info(f"Generando embeddings para {len(all_chunks)} chunks...")
    vectors = await embed_texts(all_chunks)

    save_index(all_chunks, vectors)
    logger.info(f"Indice guardado con {len(all_chunks)} chunks en {knowledge_dir}/index.json")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
