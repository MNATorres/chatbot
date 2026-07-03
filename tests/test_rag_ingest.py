"""Tests del script de ingesta: mockeamos embeddings y el guardado del indice
para no depender de la API de OpenAI, solo tocamos el filesystem real via
`tmp_path` para los documentos fuente."""

from unittest.mock import AsyncMock

from chatbot.rag import ingest


async def test_run_no_hace_nada_sin_documentos(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest.settings, "RAG_KNOWLEDGE_DIR", str(tmp_path))
    save_mock = AsyncMock()
    monkeypatch.setattr(ingest, "save_index", save_mock)

    await ingest._run()

    save_mock.assert_not_called()


async def test_run_chunkea_embeddea_y_guarda_el_indice(tmp_path, monkeypatch):
    (tmp_path / "doc1.md").write_text("Parrafo uno.\n\nParrafo dos.", encoding="utf-8")
    monkeypatch.setattr(ingest.settings, "RAG_KNOWLEDGE_DIR", str(tmp_path))

    embed_mock = AsyncMock(return_value=[[0.1], [0.2]])
    monkeypatch.setattr(ingest, "embed_texts", embed_mock)

    save_calls = []
    monkeypatch.setattr(ingest, "save_index", lambda chunks, vectors: save_calls.append((chunks, vectors)))

    await ingest._run()

    embed_mock.assert_awaited_once_with(["Parrafo uno.\n\nParrafo dos."])
    assert save_calls == [(["Parrafo uno.\n\nParrafo dos."], [[0.1], [0.2]])]
