import asyncio

from anthropic import AsyncAnthropic
from loguru import logger
from chatbot.config import settings
from chatbot.mcp_client import MCPClientManager
from chatbot.memory import ConversationMemory

# Presupuesto de salida por turno. 1024 cortaba respuestas largas (ej: listar
# 50 filas + resumen de varios canales) a mitad de palabra.
MAX_TOKENS = 8192


class ChatbotHost:
    """Actúa como el 'Host' central, inyectando dependencias al modelo de IA."""

    def __init__(self, memory: ConversationMemory | None = None):
        self.anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Memoria conversacional (MySQL). Construirla no toca la DB: solo guarda
        # la session factory; inyectable en tests.
        self.memory = memory or ConversationMemory(
            max_mensajes=settings.MEMORY_MAX_MESSAGES,
            ttl_segundos=settings.MEMORY_TTL_SECONDS,
        )

    async def _run_tool(self, mcp_client: MCPClientManager, tool_use) -> dict:
        """Ejecuta una tool vía el cliente MCP y devuelve su bloque tool_result."""
        # ➡ EL HOST LE ORDENA AL CLIENTE MCP EJECUTAR EL COMANDO
        result = await mcp_client.call_tool(tool_use.name, arguments=tool_use.input)
        result_text = result.content[0].text

        # Truncar textos ridículamente largos (ej: SELECT * de bases gigantes)
        if len(result_text) > 40000:
            result_text = result_text[:40000] + "\n...[TRUNCADO POR LONGITUD MÁXIMA ALCANZADA]"

        logger.debug(f"📊 Resultado desde MCP Server: {result_text[:100]}...")

        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": result_text,
        }

    async def process_message(
        self, message: str, mcp_client: MCPClientManager, conversation_id: str | None = None
    ) -> str:
        """Contiene el ciclo de razonamiento (ReAct) de 10 iteraciones de Claude.

        Con `conversation_id`, el turno arranca con el historial vigente de esa
        conversación y el par (mensaje, respuesta final) se persiste al terminar.
        Sin él, el comportamiento es stateless como siempre.
        """
        historial = await self.memory.get_history(conversation_id) if conversation_id else []
        messages = [*historial, {"role": "user", "content": message}]
        logger.info(f"💬 Mensaje entrante: {message}")

        for i in range(10):
            logger.info(f"🧠 Intento de Razonamiento #{i + 1}")

            # 1. Petición a Claude
            response = await self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",  # Modelo que utilices
                max_tokens=MAX_TOKENS,
                tools=mcp_client.tools,  # Obtenido desde el cliente
                messages=messages,
            )

            # 2. Análisis del output (Logs de pensamiento y decisión)
            for block in response.content:
                if block.type == "text":
                    logger.debug(f"💭 Claude piensa: {block.text}")
                if block.type == "tool_use":
                    logger.info(f"🛠️ Claude decide usar la tool: {block.name}")
                    logger.debug(f"📝 Comando generado: {block.input}")

            # Condición de salida: Si no usó herramientas, la respuesta principal es texto final.
            if response.stop_reason != "tool_use":
                final_text = response.content[0].text
                # Si Claude se quedó sin presupuesto de salida, la respuesta está
                # cortada: avisamos en vez de devolver texto truncado en silencio.
                if response.stop_reason == "max_tokens":
                    logger.warning("⚠️ Respuesta truncada por max_tokens.")
                    final_text += (
                        "\n\n⚠️ [Respuesta truncada por longitud máxima. Pedime que continúe o acotá la consulta.]"
                    )
                return await self._responder(conversation_id, message, final_text)

            # 3. Ejecución concurrente de las tools de este turno vía cliente MCP.
            #    gather preserva el orden de la lista y cada tool_result lleva su
            #    tool_use_id, así que el emparejamiento con Claude es siempre correcto.
            tool_uses = [block for block in response.content if block.type == "tool_use"]
            tool_results_content = await asyncio.gather(
                *(self._run_tool(mcp_client, tool_use) for tool_use in tool_uses)
            )

            # 4. Alimentamos el contexto de memoria
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results_content})

        return await self._responder(
            conversation_id,
            message,
            "Lo siento, alcancé el límite de razonamiento interno sin llegar a una conclusión.",
        )

    async def _responder(self, conversation_id: str | None, message: str, final_text: str) -> str:
        """Persiste el intercambio (si la conversación tiene id) y devuelve la respuesta.

        A la memoria van SOLO los textos finales: los bloques tool_use/tool_result
        del turno viven en la lista local `messages` y no deben persistirse (un
        tool_use huérfano en el turno siguiente rompería la API).
        """
        if conversation_id:
            await self.memory.append_exchange(conversation_id, message, final_text)
        return final_text
