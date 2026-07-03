"""Vector store local: guarda los chunks + sus embeddings en un archivo JSON
y busca por similitud coseno usando NumPy, sin ninguna libreria de vectores
(chroma, faiss, etc). Pensado para entender el mecanismo, no para escalar.
"""

import json
from pathlib import Path

import numpy as np

from chatbot.config import settings


def _index_path() -> Path:
    return Path(settings.RAG_KNOWLEDGE_DIR) / "index.json"


def save_index(chunks: list[str], vectors: list[list[float]]) -> None:
    """Persiste los chunks y sus vectores. Se sobreescribe en cada ingesta."""
    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"text": chunk, "vector": vector} for chunk, vector in zip(chunks, vectors)]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _load_index() -> list[dict]:
    path = _index_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """1.0 = mismo significado, 0.0 = sin relacion, -1.0 = significado opuesto."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(query_vector: list[float], top_k: int = 3) -> list[str]:
    """Devuelve el texto de los `top_k` chunks mas parecidos a `query_vector`."""
    index = _load_index()
    if not index:
        return []

    query = np.array(query_vector)
    scored = [(_cosine_similarity(query, np.array(entry["vector"])), entry["text"]) for entry in index]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [text for _, text in scored[:top_k]]
