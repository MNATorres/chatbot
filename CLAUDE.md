# CLAUDE.md

Guía para trabajar en este repositorio. Pensada para que cualquier instancia de Claude Code
sea productiva rápido. El código y los comentarios están en español; mantén ese idioma.

## Qué es el proyecto

Backend de un **agente de IA conversacional**: recibe mensajes en lenguaje natural (HTTP,
WhatsApp o Discord), se los pasa a **Claude (Anthropic)** y le da herramientas vía **Model
Context Protocol (MCP)**. Claude razona en un bucle **ReAct** y encadena llamadas a tools
hasta producir una respuesta final.

## Comandos

```bash
uv sync                # Instalar dependencias (gestor: uv, NO pip/poetry)
docker compose up -d   # Levantar MySQL 8.0 (:3306) + phpMyAdmin (:8080)
uv run start           # Arrancar el backend FastAPI en http://127.0.0.1:8000 (reload activo)

uv run python -m chatbot.rag.ingest   # (RAG) Indexar knowledge/*.md -> knowledge/index.json (requiere OPENAI_API_KEY)

# Depurar las tools MCP de forma aislada (sin pasar por Claude):
# PowerShell:
$env:PYTHONPATH = "src"; uv run mcp dev src/chatbot/mcp_server.py

uv run pytest                              # Correr los tests
uv run pytest --cov=chatbot --cov-report=term-missing   # Con coverage
```

- Python **3.13+**. Plataforma de desarrollo: **Windows (PowerShell)**.
- **Tests** en `tests/` (pytest + pytest-asyncio, `asyncio_mode=auto`). Mockean todo lo externo
  (Anthropic, MySQL, Discord, Meta): sin red ni DB real. Cubren al 100% la lógica crítica
  (`db_tools`, `mcp_host`, `routes`, `whatsapp`). Si el server está corriendo y `uv run` falla al
  re-sincronizar (bloquea `start.exe`), usá `uv run --no-sync pytest`.

## Arquitectura (patrón Host → Client → Server de MCP)

El servidor de herramientas corre como un **proceso separado** y se comunica por `stdio`.

```
Canal (HTTP /ask · webhook WhatsApp · Discord)
  → routes.py
  → ChatbotHost.process_message   (mcp_host.py)   ← bucle ReAct con Claude
  → MCPClientManager.call_tool    (mcp_client.py) ← habla por stdio
  → mcp_server.py (FastMCP)                        ← ejecuta las @mcp.tool()
      ├─ tools/db_tools.py        → MySQL (solo lectura)
      ├─ tools/discord_tools.py   → Discord
      └─ tools/rag_tools.py       → rag/ (embeddings OpenAI + búsqueda coseno sobre knowledge/)
```

Archivos clave en `src/chatbot/`:

- **`main.py`** — App FastAPI + CORS. El `lifespan` abre el cliente MCP y crea el `ChatbotHost`,
  guardándolos en `app.state` para que las rutas los reusen.
- **`routes.py`** — Endpoints: `GET /` (health), `POST /ask`, y los webhooks de WhatsApp. El
  webhook entrante **valida la firma HMAC de Meta**, deduplica por `message.id` y **procesa en
  background** (responde `200` al toque; ver convenciones).
- **`mcp_host.py`** — `ChatbotHost`: el cerebro. Bucle ReAct de **10 iteraciones** que llama a
  Claude, ejecuta las tools que pida y le devuelve los resultados.
- **`mcp_client.py`** — `MCPClientManager`: lanza `mcp_server.py` como subproceso (`uv run python
  src/chatbot/mcp_server.py` con `PYTHONPATH=src`), lista tools y las invoca.
- **`mcp_server.py`** — Punto de entrada del servidor MCP. **Importa los módulos de `tools/`** para
  que los decoradores `@mcp.tool()` registren las herramientas.
- **`app.py`** — Instancia `FastMCP` y su `lifespan` (libera el engine de la DB al cerrar).
- **`config.py`** — `Settings` de Pydantic; lee `.env`. **Centraliza toda la config** (incluida la
  de WhatsApp): usa `settings.X`, no `os.getenv`.
- **`database.py`** — Engine async de SQLAlchemy (aiomysql) + `SessionLocal`.
- **`services/`** — `whatsapp.py` (Meta Cloud API vía httpx) y `discord_service.py` (discord.py).
- **`tools/`** — `db_tools.py`, `discord_tools.py`, y `rag_tools.py` (tool `search_knowledge_base`).
- **`rag/`** — pipeline de RAG: `chunking.py` (trocea documentos por párrafos + overlap), `embeddings.py`
  (texto→vector con OpenAI `text-embedding-3-small`; Claude no tiene API de embeddings), `store.py`
  (índice JSON local + similitud coseno con NumPy, sin base de vectores) e `ingest.py` (script manual
  que indexa `knowledge/`).

## Convenciones y cosas a tener en cuenta

- **Añadir una tool nueva**: decórala con `@mcp.tool()` en un módulo dentro de `tools/`, y
  asegúrate de que `mcp_server.py` **importe ese módulo** (si no, la tool no se registra).
- **`query_production_db` es solo lectura por diseño**: valida con lista blanca de comandos
  (`SELECT/SHOW/DESCRIBE/EXPLAIN/WITH`) y lista negra de palabras peligrosas. No relajes esta
  validación sin una buena razón; nunca habilites escritura sin pedirlo explícitamente.
- **RAG (`search_knowledge_base`)**: la búsqueda lee `knowledge/index.json`, que **no se genera solo**.
  Tras agregar o editar documentos en `knowledge/`, corré la ingesta a mano
  (`uv run python -m chatbot.rag.ingest`); requiere `OPENAI_API_KEY`. El cliente de OpenAI es *lazy*,
  así que el server MCP arranca aunque no esté configurada (RAG queda inactivo hasta indexar).
- **Modelo de Claude**: hoy está hardcodeado en `mcp_host.py`. Usa siempre IDs de modelo
  actuales y capaces (familia Claude más reciente).
- **Todo es asíncrono** (FastAPI, SQLAlchemy async, httpx). No introduzcas llamadas bloqueantes
  en el event loop.
- **Memoria conversacional** (`memory.py`): el historial vive en la tabla `chat_mensajes` de MySQL
  (se crea sola en el `lifespan` con `create_all`). Se guardan **solo pares de texto**
  usuario/asistente — nunca los bloques `tool_use`/`tool_result` del ReAct (un `tool_use` huérfano
  rompería la API). Ventana de 8 mensajes por conversación + TTL de 30 min de inactividad
  (`MEMORY_MAX_MESSAGES` / `MEMORY_TTL_SECONDS` en `Settings`). Claves: `whatsapp:{sender}` y
  `ask:{session_id}`; `POST /ask` **sin** `session_id` sigue siendo stateless.
- **Webhook de WhatsApp** (`POST /webhook/whatsapp`): es **fire-and-forget en background**, no
  síncrono. Meta reintenta si no recibe un `200` rápido (causa respuestas duplicadas), así que se
  contesta `200` de inmediato y el bucle ReAct corre en `BackgroundTasks`. Además: **valida la
  firma** `X-Hub-Signature-256` (HMAC-SHA256 del body con `WHATSAPP_APP_SECRET`) antes de procesar
  y **deduplica** por `message.id` con un `deque` acotado en `app.state`. No vuelvas a procesar el
  webhook de forma síncrona ni saltees estas validaciones.
- **Secretos**: viven en `.env` (ignorado por git). Nunca hardcodees tokens ni los subas.
  Variables de WhatsApp (todas vía `Settings`): `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`,
  `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` (**obligatorio**: sin él el webhook rechaza con
  `403`), y opcionales `WHATSAPP_API_VERSION` (default `v25.0`) y `WHATSAPP_SANDBOX` (activa el fix
  de números AR del sandbox; debe estar en `false` en producción). Para el RAG: `OPENAI_API_KEY`
  (opcional; solo si se usa `search_knowledge_base`) y `RAG_KNOWLEDGE_DIR` (carpeta de documentos +
  índice; default `knowledge`).
- **Base de ejemplo**: el esquema `employees` (~300.024 registros) de
  [datacharmer/test_db](https://github.com/datacharmer/test_db), cargado por Docker.

## Teoría de MCP

- Hay una **skill** en `.claude/skills/mcp/` con la teoría y mejores prácticas de MCP
  (arquitectura, cliente/host, best practices) resumidas de la doc oficial y **mapeadas a
  este repo**. Se carga sola al trabajar temas de MCP; consúltala antes de tocar el Host, el
  Client, el Server o las tools.

## Git

- Rama principal: **`main`**. El usuario suele pedir commitear y pushear a `main` directamente.
- Cierra los mensajes de commit con:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
