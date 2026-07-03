"""Utilidades de chunking: partir un documento largo en fragmentos manejables
para generar un embedding por fragmento.

El chunking es a proposito simple (por parrafos + limite de tamano) para que
se pueda seguir el flujo completo sin depender de una libreria externa como
langchain o llama-index.
"""


def chunk_text(text: str, max_chars: int = 800, overlap_chars: int = 100) -> list[str]:
    """Parte `text` en fragmentos de como maximo `max_chars`, respetando parrafos.

    `overlap_chars` repite la cola de un fragmento al inicio del siguiente,
    para no perder contexto justo en el limite entre dos chunks.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph

        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)

        # Simplificacion intencional: si un parrafo individual ya supera
        # max_chars, lo truncamos en vez de partirlo por oraciones.
        current = paragraph[:max_chars] if len(paragraph) > max_chars else paragraph

    if current:
        chunks.append(current)

    return _add_overlap(chunks, overlap_chars)


def _add_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    """Prepende al inicio de cada chunk (salvo el primero) la cola del anterior."""
    if overlap_chars <= 0 or len(chunks) < 2:
        return chunks

    overlapped = [chunks[0]]
    for previous, current in zip(chunks, chunks[1:]):
        tail = previous[-overlap_chars:]
        overlapped.append(f"{tail}\n\n{current}")
    return overlapped
