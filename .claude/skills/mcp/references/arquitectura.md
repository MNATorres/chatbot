# Arquitectura de MCP (referencia)

Resumen fiel de https://modelcontextprotocol.io/docs/learn/architecture.

## Alcance

MCP se centra **solo** en el protocolo de intercambio de contexto. No dicta cómo
la app de IA usa el LLM ni cómo gestiona el contexto. El ecosistema incluye: la
especificación, los SDKs por lenguaje, herramientas de desarrollo (ej. el **MCP
Inspector**) y servidores de referencia.

## Participantes

Arquitectura cliente-servidor. Un **MCP Host** (app de IA: Claude Code, Claude
Desktop, VS Code…) abre conexiones a uno o más **MCP Servers**, creando **un MCP
Client por cada server**. Cada client mantiene una conexión **dedicada 1:1** con
su server.

- **Host**: coordina y gestiona uno o varios clients; es quien usa el LLM.
- **Client**: mantiene la conexión y obtiene contexto del server para el host.
- **Server**: programa que provee contexto (datos y acciones). Puede correr
  **local** (stdio) o **remoto** (Streamable HTTP).

Los servers locales con stdio suelen servir a **un** client; los remotos con
HTTP suelen servir a **muchos** clients.

## Dos capas

- **Data layer** (capa interna): protocolo basado en **JSON-RPC 2.0**. Define
  estructura y semántica de los mensajes: gestión de ciclo de vida, primitivos
  (tools, resources, prompts) y notifications.
- **Transport layer** (capa externa): mecanismos de comunicación, framing de
  mensajes, establecimiento de conexión y autenticación.

La misma capa de datos (JSON-RPC 2.0) funciona sobre cualquier transporte.

### Transportes

- **stdio**: usa stdin/stdout entre procesos locales de la misma máquina. Máximo
  rendimiento, sin overhead de red. **Es el que usa este repo.**
- **Streamable HTTP**: HTTP POST para mensajes cliente→servidor, con Server-Sent
  Events opcional para streaming. Habilita servers remotos y auth HTTP estándar
  (bearer tokens, API keys, headers). MCP recomienda **OAuth** para obtener tokens.

## Data Layer: el protocolo

JSON-RPC 2.0: cliente y servidor se mandan **requests** (con `id`, esperan
respuesta) y **notifications** (sin `id`, no esperan respuesta).

### Gestión del ciclo de vida

MCP es **stateful**: requiere negociar capacidades. El handshake:

1. Cliente → `initialize` con `protocolVersion`, `capabilities`, `clientInfo`.
2. Servidor → responde con su `protocolVersion`, `capabilities`, `serverInfo`.
   Si no hay versión compatible, se corta la conexión.
3. Cliente → `notifications/initialized` (listo).

`capabilities` declara qué primitivos soporta cada lado y si hay features como
notificaciones de cambios (`listChanged`).

Ejemplo (initialize request):
```json
{ "jsonrpc":"2.0","id":1,"method":"initialize","params":{
  "protocolVersion":"2025-06-18",
  "capabilities":{"elicitation":{}},
  "clientInfo":{"name":"example-client","version":"1.0.0"} } }
```

### Primitivos

Cada primitivo tiene métodos de descubrimiento (`*/list`), obtención (`*/get`) y,
a veces, ejecución (`tools/call`). El descubrimiento es dinámico.

**Que expone el SERVER:**
- **Tools**: funciones ejecutables que el LLM puede invocar (queries, llamadas a
  APIs, operaciones). Descubrir con `tools/list`, ejecutar con `tools/call`.
- **Resources**: fuentes de datos con contexto (contenido de archivos, registros
  de DB, respuestas de API). El esquema de una base es un caso típico de resource.
- **Prompts**: plantillas reutilizables (system prompts, few-shot) para
  estructurar la interacción con el LLM.

**Que expone el CLIENT** (permiten interacciones más ricas desde el server):
- **Sampling**: el server pide una completion del LLM al host
  (`sampling/createMessage`). Útil para que el server use un modelo sin incluir un
  SDK de LLM y sin atarse a un proveedor.
- **Elicitation**: el server pide información/confirmación al usuario
  (`elicitation/create`).
- **Logging**: el server manda logs al client para depuración/monitoreo.

**Utilitarios transversales:**
- **Tasks (experimental)**: envoltorios de ejecución durable para recuperar
  resultados de forma diferida y rastrear estado (cálculos caros, batch, flujos
  multi-paso).

### Tool discovery y ejecución (forma de los mensajes)

`tools/list` devuelve un array `tools`; cada tool trae:
- `name` (identificador único; usar prefijos claros, ej. `calculator_arithmetic`),
- `title` (nombre legible),
- `description` (qué hace y cuándo usarla),
- `inputSchema` (JSON Schema de los parámetros: validación + documentación).

`tools/call` recibe `{ name, arguments }`. La respuesta trae un array `content`
de objetos con `type` (`text`, imágenes, resources…). Ejemplo de resultado:
```json
{ "jsonrpc":"2.0","id":3,"result":{
  "content":[{"type":"text","text":"..."}] } }
```

### Notifications

Mensajes JSON-RPC sin `id`, sin respuesta. Ejemplo clave:
`notifications/tools/list_changed` — el server avisa que su lista de tools cambió
(solo si declaró `"listChanged": true`). El client reacciona re-listando tools.
Ventajas: entornos dinámicos, eficiencia (no polling), consistencia, tiempo real.

## Cómo lo hace una app de IA (pseudocódigo oficial)

```python
# Inicialización
async with stdio_client(server_config) as (read, write):
    async with ClientSession(read, write) as session:
        init = await session.initialize()
        if init.capabilities.tools:
            app.register_mcp_server(session, supports_tools=True)

# Descubrimiento: combina tools de todos los servers en un registro único
for session in app.mcp_server_sessions():
    tools = (await session.list_tools()).tools
    conversation.register_available_tools(tools)

# Ejecución: cuando el LLM decide usar una tool, el host la enruta al server
result = await session.call_tool(tool_name, arguments)
conversation.add_tool_result(result.content)
```
