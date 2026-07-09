"""Memoria conversacional persistida en MySQL.

Guarda SOLO pares de texto (mensaje del usuario + respuesta final del asistente)
en la tabla `chat_mensajes`. Los tool_use/tool_result intermedios del bucle ReAct
NO se persisten entre turnos: además del costo en tokens, un `tool_use` huérfano
en el turno siguiente haría fallar la API de Anthropic.

Concurrencia: cada método abre su propia sesión. Si dos mensajes del mismo
remitente están en vuelo, ambos leen el mismo historial-base y cada uno inserta
su par completo en una transacción; el historial resultante sigue alternando
roles y es válido para la API.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from chatbot.database import SessionLocal

# BIGINT en MySQL; en SQLite (tests) debe ser INTEGER para que el PK autoincremente.
_BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Base declarativa propia del módulo (el proyecto no usa ORM en otro lado)."""


class ChatMensaje(Base):
    """Una línea de conversación: quién habló (`user`/`assistant`) y qué dijo."""

    __tablename__ = "chat_mensajes"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    # Clave de la conversación: "whatsapp:{numero}" o "ask:{session_id}".
    conversation_id: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    # UTC asignado desde Python (naive): evita depender del timezone del server MySQL.
    creado_en: Mapped[datetime] = mapped_column(DateTime, index=True)


def _ahora_utc() -> datetime:
    """UTC naive, consistente con lo que se guarda en `creado_en`."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversationMemory:
    """Ventana de historial por conversación, con TTL de inactividad.

    - Ventana: se conservan los últimos `max_mensajes` mensajes por conversación.
    - TTL: si el mensaje más reciente es más viejo que `ttl_segundos`, la
      conversación expiró y arranca de cero (limpieza perezosa al leer).
    """

    def __init__(
        self,
        session_factory=SessionLocal,
        max_mensajes: int = 8,
        ttl_segundos: float = 1800.0,
    ):
        self._session_factory = session_factory
        self._max_mensajes = max_mensajes
        self._ttl = timedelta(seconds=ttl_segundos)

    async def get_history(self, conversation_id: str) -> list[dict[str, str]]:
        """Devuelve el historial vigente como [{"role", "content"}, ...] en orden.

        Si la conversación expiró por TTL, borra sus filas y devuelve [].
        """
        async with self._session_factory() as session:
            stmt = (
                select(ChatMensaje)
                .where(ChatMensaje.conversation_id == conversation_id)
                .order_by(ChatMensaje.id.desc())
                .limit(self._max_mensajes)
            )
            filas = list((await session.execute(stmt)).scalars())
            if not filas:
                return []

            # filas[0] es la más reciente (orden descendente).
            if _ahora_utc() - filas[0].creado_en > self._ttl:
                await session.execute(delete(ChatMensaje).where(ChatMensaje.conversation_id == conversation_id))
                await session.commit()
                return []

            return [{"role": f.role, "content": f.content} for f in reversed(filas)]

    async def append_exchange(self, conversation_id: str, mensaje_usuario: str, respuesta: str) -> None:
        """Registra un intercambio completo (par user + assistant) en una transacción.

        Tras insertar, recorta lo que quedó fuera de la ventana y purga (de todas
        las conversaciones) las filas más viejas que el TTL: la tabla se mantiene
        acotada sin necesidad de un job de limpieza aparte.
        """
        ahora = _ahora_utc()
        async with self._session_factory() as session:
            session.add_all(
                [
                    ChatMensaje(
                        conversation_id=conversation_id,
                        role="user",
                        content=mensaje_usuario,
                        creado_en=ahora,
                    ),
                    ChatMensaje(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=respuesta,
                        creado_en=ahora,
                    ),
                ]
            )
            await session.flush()

            # Recorte de ventana: se busca el id más viejo que entra en los
            # últimos `max_mensajes` y se borra todo lo anterior. Dos pasos en
            # vez de DELETE con subquery: MySQL no permite subconsultar la misma
            # tabla que se está borrando (error 1093).
            ids_ventana = (
                (
                    await session.execute(
                        select(ChatMensaje.id)
                        .where(ChatMensaje.conversation_id == conversation_id)
                        .order_by(ChatMensaje.id.desc())
                        .limit(self._max_mensajes)
                    )
                )
                .scalars()
                .all()
            )
            await session.execute(
                delete(ChatMensaje).where(
                    ChatMensaje.conversation_id == conversation_id,
                    ChatMensaje.id < min(ids_ventana),
                )
            )

            # Purga global de conversaciones vencidas por TTL.
            await session.execute(delete(ChatMensaje).where(ChatMensaje.creado_en < ahora - self._ttl))

            await session.commit()
