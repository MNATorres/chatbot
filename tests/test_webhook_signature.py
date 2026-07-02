"""Tests de la validación de firma HMAC del webhook de WhatsApp.

Sin esta validación cualquiera podría inyectar mensajes falsos y hacer que
enviemos WhatsApps arbitrarios desde nuestra cuenta.
"""
import hashlib
import hmac

from chatbot import routes
from chatbot.config import settings

SECRETO = "app-secret-de-prueba"
BODY = b'{"entry":[{"id":"1"}]}'


def _firma(body: bytes, secreto: str = SECRETO) -> str:
    return "sha256=" + hmac.new(secreto.encode(), body, hashlib.sha256).hexdigest()


def test_firma_valida(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", SECRETO)
    assert routes._firma_meta_valida(BODY, _firma(BODY)) is True


def test_firma_invalida(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", SECRETO)
    assert routes._firma_meta_valida(BODY, "sha256=deadbeef") is False


def test_body_alterado_invalida_la_firma(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", SECRETO)
    firma_ok = _firma(BODY)
    assert routes._firma_meta_valida(b'{"otro":"payload"}', firma_ok) is False


def test_sin_header_de_firma(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", SECRETO)
    assert routes._firma_meta_valida(BODY, None) is False


def test_header_sin_prefijo_sha256(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", SECRETO)
    firma_sin_prefijo = hmac.new(SECRETO.encode(), BODY, hashlib.sha256).hexdigest()
    assert routes._firma_meta_valida(BODY, firma_sin_prefijo) is False


def test_sin_secreto_configurado_rechaza(monkeypatch):
    # Default seguro: sin App Secret no podemos validar => rechazamos.
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", None)
    assert routes._firma_meta_valida(BODY, _firma(BODY)) is False
