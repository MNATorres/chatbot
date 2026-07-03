"""Tests del vector store: similitud coseno + top-k, sin red ni depender de
embeddings reales (usamos vectores de juguete escritos a mano)."""

from chatbot.rag import store


def test_search_devuelve_vacio_sin_indice(tmp_path, monkeypatch):
    monkeypatch.setattr(store.settings, "RAG_KNOWLEDGE_DIR", str(tmp_path))
    assert store.search([1.0, 0.0]) == []


def test_search_ordena_por_similitud_coseno(tmp_path, monkeypatch):
    monkeypatch.setattr(store.settings, "RAG_KNOWLEDGE_DIR", str(tmp_path))

    # Vectores 2D de juguete: el primero es el mas parecido a la query [1.0, 0.0].
    store.save_index(
        chunks=["muy parecido", "algo parecido", "nada parecido"],
        vectors=[[1.0, 0.1], [1.0, 0.9], [-1.0, 0.0]],
    )

    result = store.search([1.0, 0.0], top_k=2)

    assert result == ["muy parecido", "algo parecido"]


def test_search_respeta_top_k(tmp_path, monkeypatch):
    monkeypatch.setattr(store.settings, "RAG_KNOWLEDGE_DIR", str(tmp_path))
    store.save_index(
        chunks=["a", "b", "c"],
        vectors=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
    )

    assert len(store.search([1.0, 0.0], top_k=1)) == 1


def test_save_index_sobreescribe_el_anterior(tmp_path, monkeypatch):
    monkeypatch.setattr(store.settings, "RAG_KNOWLEDGE_DIR", str(tmp_path))
    store.save_index(chunks=["viejo"], vectors=[[1.0, 0.0]])
    store.save_index(chunks=["nuevo"], vectors=[[1.0, 0.0]])

    assert store.search([1.0, 0.0]) == ["nuevo"]
