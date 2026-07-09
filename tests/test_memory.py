"""Tests de `ConversationMemory` contra SQLite async en memoria.

No hay red ni Docker: `aiosqlite` corre en el proceso. A diferencia de mockear
sesiones, esto ejercita el SQL real (ventana, TTL, transacciones).
"""

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chatbot.memory import Base, ChatMensaje, ConversationMemory, _ahora_utc


@pytest.fixture
async def session_factory():
    """Engine SQLite en memoria con la tabla creada; una DB nueva por test."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


def _memoria(session_factory, **kwargs):
    return ConversationMemory(session_factory=session_factory, **kwargs)


async def test_conversacion_inexistente_devuelve_vacio(session_factory):
    memoria = _memoria(session_factory)
    assert await memoria.get_history("whatsapp:123") == []


async def test_un_intercambio_se_recupera_en_orden(session_factory):
    memoria = _memoria(session_factory)
    await memoria.append_exchange("whatsapp:123", "hola", "¡Hola! ¿En qué te ayudo?")

    historial = await memoria.get_history("whatsapp:123")
    assert historial == [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¡Hola! ¿En qué te ayudo?"},
    ]


async def test_ventana_conserva_solo_los_ultimos_pares(session_factory):
    # Ventana de 4 mensajes = 2 intercambios: el primero debe caerse.
    memoria = _memoria(session_factory, max_mensajes=4)
    await memoria.append_exchange("ask:s1", "pregunta 1", "respuesta 1")
    await memoria.append_exchange("ask:s1", "pregunta 2", "respuesta 2")
    await memoria.append_exchange("ask:s1", "pregunta 3", "respuesta 3")

    historial = await memoria.get_history("ask:s1")
    assert [m["content"] for m in historial] == [
        "pregunta 2",
        "respuesta 2",
        "pregunta 3",
        "respuesta 3",
    ]
    assert [m["role"] for m in historial] == ["user", "assistant", "user", "assistant"]


async def test_ttl_vencido_devuelve_vacio_y_borra(session_factory):
    memoria = _memoria(session_factory, ttl_segundos=1800)
    await memoria.append_exchange("whatsapp:123", "hola", "¡Hola!")

    # Envejecemos las filas más allá del TTL directamente en la DB.
    async with session_factory() as session:
        for fila in (await session.execute(ChatMensaje.__table__.select())).all():
            await session.execute(
                ChatMensaje.__table__.update()
                .where(ChatMensaje.id == fila.id)
                .values(creado_en=_ahora_utc() - timedelta(seconds=3600))
            )
        await session.commit()

    assert await memoria.get_history("whatsapp:123") == []
    # La limpieza perezosa borró las filas: la tabla queda vacía.
    async with session_factory() as session:
        assert (await session.execute(ChatMensaje.__table__.select())).all() == []


async def test_conversaciones_aisladas_entre_si(session_factory):
    memoria = _memoria(session_factory)
    await memoria.append_exchange("whatsapp:111", "soy Ana", "Hola Ana")
    await memoria.append_exchange("whatsapp:222", "soy Juan", "Hola Juan")

    historial = await memoria.get_history("whatsapp:111")
    assert all("Juan" not in m["content"] for m in historial)
    assert len(historial) == 2


async def test_persiste_entre_instancias(session_factory):
    # Simula un reinicio del server: otra instancia sobre la misma DB ve el historial.
    await _memoria(session_factory).append_exchange("ask:abc", "hola", "¡Hola!")
    historial = await _memoria(session_factory).get_history("ask:abc")
    assert len(historial) == 2


async def test_purga_global_de_conversaciones_vencidas(session_factory):
    memoria = _memoria(session_factory, ttl_segundos=1800)
    await memoria.append_exchange("whatsapp:viejo", "hola", "¡Hola!")

    # Envejecemos la conversación "viejo" más allá del TTL.
    async with session_factory() as session:
        await session.execute(
            ChatMensaje.__table__.update()
            .where(ChatMensaje.conversation_id == "whatsapp:viejo")
            .values(creado_en=_ahora_utc() - timedelta(seconds=3600))
        )
        await session.commit()

    # Un append en OTRA conversación dispara la purga global.
    await memoria.append_exchange("whatsapp:nuevo", "buenas", "¡Buenas!")

    async with session_factory() as session:
        filas = (await session.execute(ChatMensaje.__table__.select())).all()
    assert {f.conversation_id for f in filas} == {"whatsapp:nuevo"}
