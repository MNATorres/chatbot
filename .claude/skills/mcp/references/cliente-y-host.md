# Construir un Cliente y un Host MCP (referencia)

Basado en https://modelcontextprotocol.io/docs/develop/build-client y en la
arquitectura oficial. Adaptado a **nuestro** stack (Python + `mcp` SDK +
`anthropic` + FastMCP por stdio).

## Diferencia Host vs Client (importante)

- El **Client** es la pieza de plomería: abre el transporte, hace `initialize`,
  `list_tools`, `call_tool`. Es 1:1 con un server. Aquí: `MCPClientManager`.
- El **Host** es la lógica de aplicación: mantiene la conversación, habla con el
  LLM, decide, y **orquesta** las llamadas a tools a través del/los client(s).
  Aquí: `ChatbotHost`. El bucle de razonamiento (ReAct) es responsabilidad del host.

Los tutoriales oficiales juntan ambos en una clase `MCPClient` por simplicidad;
**este repo los separa bien**, que es la forma correcta de escalar.

## Anatomía de un client (patrón oficial, Python)

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(command="python", args=[server_script], env=None)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()                      # handshake
        tools = (await session.list_tools()).tools      # descubrimiento
        result = await session.call_tool(name, args)    # ejecución
```

Puntos clave del tutorial:
- Gestión de recursos con `AsyncExitStack` (o `async with`, como aquí) para
  cerrar limpio.
- Al listar tools, mapearlas al formato que espera el LLM:
  `{"name", "description", "input_schema": tool.inputSchema}`.
- La primera respuesta puede tardar ~30 s (arranque del server + LLM + tools).

### Cómo lo hace este repo (`mcp_client.py`)

`MCPClientManager` encapsula la `ClientSession`; `get_mcp_client()` es un
`@asynccontextmanager` que lanza el server como subproceso:

```python
server_params = StdioServerParameters(
    command="uv",
    args=["run", "python", "src/chatbot/mcp_server.py"],
    env={**os.environ, "PYTHONPATH": "src"},   # PYTHONPATH=src para que importe chatbot.*
)
```
`initialize()` hace `session.initialize()` + `list_tools()` y guarda las tools ya
mapeadas al formato de la API de Anthropic. `call_tool()` delega en la sesión.

## El bucle de "tool use" / ReAct (responsabilidad del Host)

Patrón oficial (simplificado): mandar el query a Claude con las tools; si Claude
pide una tool, ejecutarla, devolver el `tool_result`, y repetir hasta que Claude
conteste con texto final.

```python
messages = [{"role": "user", "content": query}]
resp = anthropic.messages.create(model=<ID_ACTUAL>, max_tokens=..., tools=tools, messages=messages)

for content in resp.content:
    if content.type == "tool_use":
        result = await session.call_tool(content.name, content.input)
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": [{
            "type": "tool_result", "tool_use_id": content.id, "content": result.content }]})
        resp = anthropic.messages.create(...)   # siguiente turno
```

### Cómo lo hace este repo (`mcp_host.py`)

`ChatbotHost.process_message` implementa un bucle ReAct de **10 iteraciones**:
1. Llama a Claude con `tools=mcp_client.tools`.
2. Si `stop_reason != "tool_use"` → devuelve el texto final.
3. Si pide tools: las ejecuta vía `mcp_client.call_tool`, trunca resultados >40k
   chars, arma los `tool_result` y realimenta `messages`.
4. Si agota las 10 iteraciones, devuelve un mensaje de "límite alcanzado".

Tiene **memoria conversacional opcional** (`memory.py`): con `conversation_id`
(`whatsapp:{sender}` o `ask:{session_id}`), el turno arranca con el historial de la
tabla `chat_mensajes` (MySQL) y persiste el par texto usuario/respuesta final al
terminar — nunca los bloques `tool_use`/`tool_result`. Sin `conversation_id`
(ej: `/ask` sin `session_id`), cada mensaje arranca una conversación nueva.

## Diferencias con el tutorial y mejoras a tener en cuenta

El tutorial oficial es intencionadamente básico. Cosas a vigilar / mejorar aquí:

1. **`return response.content[0].text`** (host) asume que el primer bloque final
   es texto. Con *extended thinking* u otro bloque inicial puede romper. Más
   robusto: buscar el primer bloque `type == "text"`.
2. **`result.content[0].text`** asume que la tool devolvió texto en el primer
   bloque. El estándar permite varios bloques y tipos; conviene concatenar todos
   los `type=="text"` y contemplar `isError`.
3. **Manejo de errores de tool**: en MCP un error de tool llega como respuesta
   normal con `isError: true` (no como fallo de transporte). Conviene detectarlo
   y devolvérselo al LLM para que se autocorrija, en vez de tratarlo como éxito.
4. **Un solo client compartido** entre peticiones concurrentes: la sesión stdio
   es única. Para carga real, revisar concurrencia (una sesión por request, un
   pool, o serializar).
5. **Modelo**: el tutorial usa `claude-sonnet-4-20250514`; **desactualizado**.
   Usa el ID de la familia Claude más reciente y capaz.
6. **Timeouts**: configura timeouts en las llamadas a tools; si una tool cuelga,
   el bucle no debería quedarse bloqueado indefinidamente.

## Depurar el server aislado (sin pasar por Claude)

```powershell
$env:PYTHONPATH = "src"; uv run mcp dev src/chatbot/mcp_server.py
```
Abre el **MCP Inspector**: lista tools, prueba `tools/call` a mano, y verifica
`inputSchema`. Ideal para desarrollar/depurar una tool nueva antes de exponerla
al agente.
