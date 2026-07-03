"""Tests del cliente de embeddings: mockeamos el cliente de OpenAI para no
pegarle a la API real ni depender de una API key configurada."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from chatbot.rag import embeddings


def _fake_response(vectors):
    return SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vectors])


def _install_fake_client(monkeypatch, vectors):
    fake_client = MagicMock()
    fake_client.embeddings.create = AsyncMock(return_value=_fake_response(vectors))
    monkeypatch.setattr(embeddings, "_client", fake_client)
    return fake_client


async def test_embed_text_devuelve_el_vector_del_primer_resultado(monkeypatch):
    fake_client = _install_fake_client(monkeypatch, [[0.1, 0.2]])

    result = await embeddings.embed_text("hola")

    assert result == [0.1, 0.2]
    fake_client.embeddings.create.assert_awaited_once_with(model=embeddings.EMBEDDING_MODEL, input="hola")


async def test_embed_texts_devuelve_un_vector_por_texto_en_orden(monkeypatch):
    fake_client = _install_fake_client(monkeypatch, [[1.0], [2.0], [3.0]])

    result = await embeddings.embed_texts(["a", "b", "c"])

    assert result == [[1.0], [2.0], [3.0]]
    fake_client.embeddings.create.assert_awaited_once_with(model=embeddings.EMBEDDING_MODEL, input=["a", "b", "c"])


def test_get_client_reutiliza_la_misma_instancia(monkeypatch):
    monkeypatch.setattr(embeddings, "_client", None)
    monkeypatch.setattr(embeddings.settings, "OPENAI_API_KEY", "test-key")

    first = embeddings._get_client()
    second = embeddings._get_client()

    assert first is second
