import asyncio

from anthropic import AsyncAnthropic
from chatbot.mcp_client import MCPClientManager

class ChatbotHost:
    """Actúa como el 'Host' central, inyectando dependencias al modelo de IA."""
    def __init__(self):
        self.anthropic = AsyncAnthropic()

    async def _run_tool(self, mcp_client: MCPClientManager, tool_use) -> dict:
        """Ejecuta una tool vía el cliente MCP y devuelve su bloque tool_result."""
        # ➡ EL HOST LE ORDENA AL CLIENTE MCP EJECUTAR EL COMANDO
        result = await mcp_client.call_tool(tool_use.name, arguments=tool_use.input)
        result_text = result.content[0].text

        # Truncar textos ridículamente largos (ej: SELECT * de bases gigantes)
        if len(result_text) > 40000:
            result_text = result_text[:40000] + "\n...[TRUNCADO POR LONGITUD MÁXIMA ALCANZADA]"

        print(f"📊 Resultado desde MCP Server: {result_text[:100]}...")

        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": result_text,
        }

    async def process_message(self, message: str, mcp_client: MCPClientManager) -> str:
        """Contiene el ciclo de razonamiento (ReAct) de 10 iteraciones de Claude."""
        messages = [{"role": "user", "content": message}]
        
        for i in range(10):
            print(f"\n--- 🧠 Intento de Razonamiento #{i+1} ---")
            
            # 1. Petición a Claude
            response = await self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929", # Modelo que utilices
                max_tokens=1024,
                tools=mcp_client.tools,  # Obtenido desde el cliente
                messages=messages
            )

            # 2. Análisis del output (Logs de pensamiento y decisión)
            for block in response.content:
                if block.type == "text":
                    print(f"💭 Claude piensa: {block.text}")
                if block.type == "tool_use":
                    print(f"🛠️ Claude decide usar la tool: {block.name}")
                    print(f"📝 Comando generado: {block.input}")

            # Condición de salida: Si no usó herramientas, la respuesta principal es texto final.
            if response.stop_reason != "tool_use":
                return response.content[0].text

            # 3. Ejecución concurrente de las tools de este turno vía cliente MCP.
            #    gather preserva el orden de la lista y cada tool_result lleva su
            #    tool_use_id, así que el emparejamiento con Claude es siempre correcto.
            tool_uses = [block for block in response.content if block.type == "tool_use"]
            tool_results_content = await asyncio.gather(
                *(self._run_tool(mcp_client, tool_use) for tool_use in tool_uses)
            )

            # 4. Alimentamos el contexto de memoria
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": tool_results_content
            })
            
        return "Lo siento, alcancé el límite de razonamiento interno sin llegar a una conclusión."
