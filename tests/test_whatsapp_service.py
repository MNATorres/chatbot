"""Tests de `send_whatsapp_message`: reescritura de números en sandbox,
éxito y manejo de errores HTTP. httpx se mockea (sin red)."""
import httpx
import pytest

from chatbot.config import settings
from chatbot.services import whatsapp
from chatbot.services.whatsapp import send_whatsapp_message


class _FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = "error body"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=self)


class _FakeAsyncClient:
    """Reemplaza a httpx.AsyncClient; captura la última llamada POST."""
    ultima_llamada = {}

    def __init__(self, status_code=200):
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeAsyncClient.ultima_llamada = {"url": url, "json": json, "headers": headers}
        return _FakeResponse(self._status_code)


@pytest.fixture(autouse=True)
def _credenciales(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "token-x")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_ID", "12345")
    monkeypatch.setattr(settings, "WHATSAPP_API_VERSION", "v25.0")


def _patch_client(monkeypatch, status_code=200):
    monkeypatch.setattr(whatsapp.httpx, "AsyncClient", lambda: _FakeAsyncClient(status_code))


async def test_envio_exitoso_devuelve_true(monkeypatch):
    _patch_client(monkeypatch)
    monkeypatch.setattr(settings, "WHATSAPP_SANDBOX", False)

    ok = await send_whatsapp_message("5491111111111", "hola")

    assert ok is True
    llamada = _FakeAsyncClient.ultima_llamada
    assert "12345/messages" in llamada["url"]
    assert llamada["json"]["to"] == "5491111111111"
    assert llamada["headers"]["Authorization"] == "Bearer token-x"


async def test_sandbox_reescribe_numero_argentino(monkeypatch):
    _patch_client(monkeypatch)
    monkeypatch.setattr(settings, "WHATSAPP_SANDBOX", True)

    await send_whatsapp_message("5491122223333", "hola")

    assert _FakeAsyncClient.ultima_llamada["json"]["to"] == "54111522223333"


async def test_sin_sandbox_no_reescribe(monkeypatch):
    _patch_client(monkeypatch)
    monkeypatch.setattr(settings, "WHATSAPP_SANDBOX", False)

    await send_whatsapp_message("5491122223333", "hola")

    assert _FakeAsyncClient.ultima_llamada["json"]["to"] == "5491122223333"


async def test_error_http_devuelve_false(monkeypatch):
    _patch_client(monkeypatch, status_code=400)
    monkeypatch.setattr(settings, "WHATSAPP_SANDBOX", False)

    ok = await send_whatsapp_message("5491111111111", "hola")

    assert ok is False


async def test_error_de_red_devuelve_false(monkeypatch):
    # Falla genérica (ej: timeout / conexión): no debe propagar, devuelve False.
    monkeypatch.setattr(settings, "WHATSAPP_SANDBOX", False)

    class _ClientQueExplota:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *a, **kw):
            raise httpx.ConnectError("sin red")

    monkeypatch.setattr(whatsapp.httpx, "AsyncClient", lambda: _ClientQueExplota())

    ok = await send_whatsapp_message("5491111111111", "hola")

    assert ok is False
