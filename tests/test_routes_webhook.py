"""Tests del webhook de WhatsApp end-to-end (con TestClient): firma, dedup,
manejo de no-texto, verificación GET y disparo del procesamiento en background."""

import hashlib
import hmac
import json
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot import routes
from chatbot.config import settings

SECRETO = "app-secret-de-prueba"
VERIFY_TOKEN = "verify-123"


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", SECRETO)
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)


@pytest.fixture
def enviar_mock(monkeypatch):
    """Mockea send_whatsapp_message en el namespace de routes."""
    mock = AsyncMock()
    monkeypatch.setattr(routes, "send_whatsapp_message", mock)
    return mock


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(routes.router)
    app.state.mcp_host = MagicMock()
    app.state.mcp_host.process_message = AsyncMock(return_value="respuesta del bot")
    app.state.mcp_client = MagicMock()
    app.state.whatsapp_seen_ids = deque(maxlen=1000)
    return app


def _payload(message_id="wamid.1", tipo="text", body="hola"):
    mensaje = {"id": message_id, "from": "5491111111111", "type": tipo}
    if tipo == "text":
        mensaje["text"] = {"body": body}
    return {"entry": [{"changes": [{"value": {"messages": [mensaje]}}]}]}


def _firma(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRETO.encode(), body, hashlib.sha256).hexdigest()


def _post(client, payload, firmar=True):
    body = json.dumps(payload).encode()
    headers = {"X-Hub-Signature-256": _firma(body)} if firmar else {}
    return client.post("/webhook/whatsapp", content=body, headers=headers)


# --- Firma ---


def test_firma_invalida_devuelve_403(app, enviar_mock):
    with TestClient(app) as client:
        body = json.dumps(_payload()).encode()
        r = client.post("/webhook/whatsapp", content=body, headers={"X-Hub-Signature-256": "sha256=malo"})
    assert r.status_code == 403
    app.state.mcp_host.process_message.assert_not_called()


def test_sin_header_de_firma_devuelve_403(app, enviar_mock):
    with TestClient(app) as client:
        r = _post(client, _payload(), firmar=False)
    assert r.status_code == 403


# --- Mensaje de texto válido: 200 + procesamiento en background ---


def test_mensaje_texto_valido_dispara_procesamiento(app, enviar_mock):
    with TestClient(app) as client:
        r = _post(client, _payload(body="cuántos empleados hay"))
    assert r.status_code == 200
    app.state.mcp_host.process_message.assert_awaited_once()
    args, kwargs = app.state.mcp_host.process_message.call_args
    assert args[0] == "cuántos empleados hay"
    # Cada número de WhatsApp tiene su propia conversación con memoria.
    assert kwargs["conversation_id"] == "whatsapp:5491111111111"
    enviar_mock.assert_awaited_once_with("5491111111111", "respuesta del bot")


# --- Deduplicación ---


def test_mensaje_duplicado_se_procesa_una_sola_vez(app, enviar_mock):
    with TestClient(app) as client:
        r1 = _post(client, _payload(message_id="wamid.dup"))
        r2 = _post(client, _payload(message_id="wamid.dup"))
    assert r1.status_code == 200 and r2.status_code == 200
    assert app.state.mcp_host.process_message.await_count == 1


# --- No-texto ---


def test_mensaje_no_texto_avisa_y_no_procesa(app, enviar_mock):
    with TestClient(app) as client:
        r = _post(client, _payload(tipo="image"))
    assert r.status_code == 200
    app.state.mcp_host.process_message.assert_not_called()
    enviar_mock.assert_awaited_once()
    _, msg = enviar_mock.call_args[0]
    assert "texto" in msg.lower()


# --- Payload sin 'messages' (notificación de estado) se ignora ---


def test_notificacion_sin_messages_se_ignora(app, enviar_mock):
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    with TestClient(app) as client:
        r = _post(client, payload)
    assert r.status_code == 200
    app.state.mcp_host.process_message.assert_not_called()


# --- Verificación GET del webhook ---


def test_verificacion_get_token_correcto(app):
    with TestClient(app) as client:
        r = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "998877",
                "hub.verify_token": VERIFY_TOKEN,
            },
        )
    assert r.status_code == 200
    assert r.json() == 998877


def test_verificacion_get_token_incorrecto(app):
    with TestClient(app) as client:
        r = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "998877",
                "hub.verify_token": "token-equivocado",
            },
        )
    assert r.status_code == 403


# --- Payload firmado pero malformado (no se procesa, no rompe) ---


def test_payload_no_json_se_ignora(app, enviar_mock):
    body = b"esto no es json"
    with TestClient(app) as client:
        r = client.post("/webhook/whatsapp", content=body, headers={"X-Hub-Signature-256": _firma(body)})
    assert r.status_code == 200
    assert r.json() == {"status": "ignored"}
    app.state.mcp_host.process_message.assert_not_called()


# --- Una excepción en el procesamiento no debe romper (se loguea) ---


def test_error_en_procesamiento_no_crashea(app, enviar_mock):
    app.state.mcp_host.process_message = AsyncMock(side_effect=RuntimeError("boom"))
    with TestClient(app) as client:
        r = _post(client, _payload(message_id="wamid.err"))
    assert r.status_code == 200
    # El envío no llega a ejecutarse porque el procesamiento falló antes.
    enviar_mock.assert_not_awaited()


# --- Endpoint /ask ---


def test_ask_delega_al_host(app):
    with TestClient(app) as client:
        r = client.post("/ask", json={"message": "hola"})
    assert r.status_code == 200
    assert r.json() == {"answer": "respuesta del bot"}
    app.state.mcp_host.process_message.assert_awaited_once()


def test_ask_sin_session_id_es_stateless(app):
    with TestClient(app) as client:
        client.post("/ask", json={"message": "hola"})
    kwargs = app.state.mcp_host.process_message.call_args.kwargs
    assert kwargs["conversation_id"] is None


def test_ask_con_session_id_pasa_conversation_id(app):
    with TestClient(app) as client:
        client.post("/ask", json={"message": "hola", "session_id": "abc"})
    kwargs = app.state.mcp_host.process_message.call_args.kwargs
    assert kwargs["conversation_id"] == "ask:abc"


# --- Health check ---


def test_health_check_reporta_mcp_conectado(app):
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "online", "mcp_connected": True}
