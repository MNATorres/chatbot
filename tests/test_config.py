"""Tests de `Settings`: defaults seguros y validación de secretos obligatorios.

Se construye `Settings(_env_file=None)` para que el `.env` local del desarrollador
no contamine los asserts; las env vars del proceso se limpian con monkeypatch.
"""

from chatbot.config import Settings


def test_debug_es_false_por_defecto(monkeypatch):
    # Sin .env ni env var, DEBUG debe quedar apagado (evita diagnose=True en prod).
    monkeypatch.delenv("DEBUG", raising=False)
    assert Settings(_env_file=None).DEBUG is False


def test_secretos_de_canales_son_opcionales(monkeypatch):
    # WhatsApp/Discord/OpenAI son canales/funciones desactivables: la app debe
    # poder construirse sin ellos.
    for var in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "WHATSAPP_TOKEN",
        "WHATSAPP_PHONE_ID",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_APP_SECRET",
        "DISCORD_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)
    assert settings.WHATSAPP_TOKEN is None
    assert settings.DISCORD_TOKEN is None
    assert settings.OPENAI_API_KEY is None
