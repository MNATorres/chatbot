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

# Depurar las tools MCP de forma aislada (sin pasar por Claude):
# PowerShell:
$env:PYTHONPATH = "src"; uv run mcp dev src/chatbot/mcp_server.py
```

- Python **3.13+**. Plataforma de desarrollo: **Windows (PowerShell)**.
- No hay tests todavía (`tests/` está vacío).

## Arquitectura (patrón Host → Client → Server de MCP)

El servidor de herramientas corre como un **proceso separado** y se comunica por `stdio`.

```
Canal (HTTP /ask · webhook WhatsApp · Discord)
  → routes.py
  → ChatbotHost.process_message   (mcp_host.py)   ← bucle ReAct con Claude
  → MCPClientManager.call_tool    (mcp_client.py) ← habla por stdio
  → mcp_server.py (FastMCP)                        ← ejecuta las @mcp.tool()
      ├─ tools/db_tools.py        → MySQL (solo lectura)
      └─ tools/discord_tools.py   → Discord
```

Archivos clave en `src/chatbot/`:

- **`main.py`** — App FastAPI + CORS. El `lifespan` abre el cliente MCP y crea el `ChatbotHost`,
  guardándolos en `app.state` para que las rutas los reusen.
- **`routes.py`** — Endpoints: `GET /` (health), `POST /ask`, y los webhooks de WhatsApp.
- **`mcp_host.py`** — `ChatbotHost`: el cerebro. Bucle ReAct de **10 iteraciones** que llama a
  Claude, ejecuta las tools que pida y le devuelve los resultados.
- **`mcp_client.py`** — `MCPClientManager`: lanza `mcp_server.py` como subproceso (`uv run python
  src/chatbot/mcp_server.py` con `PYTHONPATH=src`), lista tools y las invoca.
- **`mcp_server.py`** — Punto de entrada del servidor MCP. **Importa los módulos de `tools/`** para
  que los decoradores `@mcp.tool()` registren las herramientas.
- **`app.py`** — Instancia `FastMCP` y su `lifespan` (libera el engine de la DB al cerrar).
- **`config.py`** — `Settings` de Pydantic; lee `.env`.
- **`database.py`** — Engine async de SQLAlchemy (aiomysql) + `SessionLocal`.
- **`services/`** — `whatsapp.py` (Meta Cloud API vía httpx) y `discord_service.py` (discord.py).
- **`tools/`** — `db_tools.py`, `discord_tools.py`, y `rag_tools.py` (**vacío, reservado para RAG**).

## Convenciones y cosas a tener en cuenta

- **Añadir una tool nueva**: decórala con `@mcp.tool()` en un módulo dentro de `tools/`, y
  asegúrate de que `mcp_server.py` **importe ese módulo** (si no, la tool no se registra).
- **`query_production_db` es solo lectura por diseño**: valida con lista blanca de comandos
  (`SELECT/SHOW/DESCRIBE/EXPLAIN/WITH`) y lista negra de palabras peligrosas. No relajes esta
  validación sin una buena razón; nunca habilites escritura sin pedirlo explícitamente.
- **Modelo de Claude**: hoy está hardcodeado en `mcp_host.py`. Usa siempre IDs de modelo
  actuales y capaces (familia Claude más reciente).
- **Todo es asíncrono** (FastAPI, SQLAlchemy async, httpx). No introduzcas llamadas bloqueantes
  en el event loop.
- **El agente es stateless**: cada mensaje arranca una conversación nueva, sin historial entre
  peticiones.
- **Secretos**: viven en `.env` (ignorado por git). Nunca hardcodees tokens ni los subas.
- **Base de ejemplo**: el esquema `employees` (~300.024 registros) de
  [datacharmer/test_db](https://github.com/datacharmer/test_db), cargado por Docker.

## Git

- Rama principal: **`main`**. El usuario suele pedir commitear y pushear a `main` directamente.
- Cierra los mensajes de commit con:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
