# src/chatbot/tools/discord_tools.py
from chatbot.app import mcp
from chatbot.services.discord_service import send_discord_message, fetch_channel_history, fetch_all_channels


@mcp.tool()
async def send_message_to_channel(channel_id: str, message: str) -> str:
    """Envía un mensaje de texto a un canal específico de Discord."""
    success = await send_discord_message(int(channel_id), message)
    return "Mensaje enviado con éxito" if success else "Error al enviar el mensaje"


@mcp.tool()
async def read_channel_messages(channel_id: str, limit: int = 10) -> str:
    """Lee los últimos mensajes de un canal de Discord para obtener contexto."""
    messages = await fetch_channel_history(int(channel_id), limit)
    return str(messages)


@mcp.tool()
async def list_discord_channels() -> str:
    """Obtiene la lista de todos los canales de texto de Discord disponibles con sus respectivos IDs y nombres."""
    channels = await fetch_all_channels()
    if not channels:
        return "No se encontraron canales o hubo un error al obtenerlos."
    return "\n".join(channels)
