---
name: mcp
description: >-
  Teoría y mejores prácticas del Model Context Protocol (MCP) aplicadas a ESTE
  repositorio (agente ReAct con Claude + FastMCP por stdio). Úsala SIEMPRE que
  trabajes con MCP en este proyecto: el Host (mcp_host.py), el Client
  (mcp_client.py), el Server (mcp_server.py / app.py), las tools de tools/, el
  ciclo de vida (initialize, list_tools, call_tool), el bucle de tool use / ReAct,
  el transporte stdio, los primitivos (tools, resources, prompts, sampling,
  elicitation), notifications, o cuando toque diseñar/depurar/ampliar cualquiera
  de esas piezas. Fuente: documentación oficial de modelcontextprotocol.io.
---

# Model Context Protocol (MCP) — teoría y práctica para este repo

Guía de referencia para trabajar MCP en este proyecto. Resume la documentación
oficial (`modelcontextprotocol.io`) y la **conecta con nuestro código real**.
Todo en español, como el resto del repo.

## Cómo usar esta skill

- Lee primero este `SKILL.md` (panorama + mapeo al repo).
- Para profundizar, abre el archivo de referencia que corresponda:
  - `references/arquitectura.md` — participantes, capas, JSON-RPC, ciclo de vida,
    primitivos, notifications, transportes. (Con ejemplos de mensajes.)
  - `references/cliente-y-host.md` — cómo se construye un cliente y un host MCP,
    el patrón del bucle de tool use, y cómo lo implementamos aquí.
  - `references/best-practices.md` — buenas prácticas: progressive discovery,
    programmatic tool calling, seguridad, manejo de errores, caching.

## MCP en 30 segundos

MCP es un protocolo **cliente-servidor** para darle **contexto** (datos) y
**acciones** (herramientas) a una aplicación de IA, de forma estándar y
model-independent. Tres participantes:

- **Host** — la app de IA que coordina uno o varios clients y usa el LLM.
- **Client** — mantiene **una** conexión dedicada **1:1** con un server.
- **Server** — programa que expone tools/resources/prompts. Puede ser local
  (transporte **stdio**) o remoto (**Streamable HTTP**).

Dos capas: **data layer** (protocolo JSON-RPC 2.0: ciclo de vida + primitivos)
y **transport layer** (stdio o HTTP). MCP es **stateful**: arranca con un
handshake `initialize` que **negocia capacidades**.

> ⚠️ MCP solo define *el protocolo de intercambio de contexto*. NO dicta cómo
> la app usa el LLM ni cómo gestiona el contexto: eso es responsabilidad del host.

## Cómo se mapea a ESTE repositorio

Este proyecto implementa el patrón **Host → Client → Server** de manual:

| Concepto MCP | Dónde vive aquí | Notas |
|---|---|---|
| **Host** | `src/chatbot/mcp_host.py` (`ChatbotHost`) | Bucle ReAct de 10 iteraciones; habla con Claude y orquesta las tools. |
| **Client** | `src/chatbot/mcp_client.py` (`MCPClientManager`) | `initialize` → `list_tools` → `call_tool`. Lanza el server por stdio. |
| **Server** | `src/chatbot/mcp_server.py` + `app.py` (`FastMCP`) | Subproceso independiente; registra tools al importar los módulos de `tools/`. |
| **Transporte** | **stdio** | El server corre como subproceso local (`uv run python ... PYTHONPATH=src`). |
| **Tools** (primitivo de server) | `tools/db_tools.py`, `tools/discord_tools.py` | Decoradas con `@mcp.tool()`. |
| **Resources / Prompts** | *(no usados aún)* | Oportunidad de mejora: exponer el esquema de la DB como *resource*. |
| **Ciclo de vida** | `main.py` lifespan + `app.py` `app_lifespan` | Abre el client al arrancar FastAPI; libera el engine al cerrar. |

Flujo de una petición:

```
/ask · webhook WhatsApp  →  routes.py
  → ChatbotHost.process_message   (Host: bucle ReAct con Claude)
  → MCPClientManager.call_tool    (Client: JSON-RPC por stdio)
  → mcp_server.py (FastMCP)       (Server: ejecuta la @mcp.tool())
```

## Reglas de oro al tocar MCP en este repo

1. **Registrar tools**: una tool solo existe si su módulo se **importa** en
   `mcp_server.py`. Añadir `@mcp.tool()` no basta si nadie importa el módulo.
2. **`tools/list` es dinámico**: el client descubre tools en runtime; no
   hardcodees la lista. Si el server declara `listChanged`, puede notificar
   cambios (`notifications/tools/list_changed`).
3. **El resultado de una tool es un array `content`** (normalmente `type:"text"`).
   Aquí leemos `result.content[0].text` — ver limitaciones en `cliente-y-host.md`.
4. **Modelo de Claude**: usa SIEMPRE un ID actual y capaz (familia Claude más
   reciente). Los tutoriales oficiales citan modelos viejos
   (`claude-sonnet-4-*`): **no los copies**, están desactualizados.
5. **Seguridad**: las tools son superficie de ataque. `query_production_db` es
   solo lectura por diseño (lista blanca + lista negra). No relajes esa
   validación. Trata el output de una tool como entrada no confiable.
6. **Todo async, no bloquear el event loop**. Transporte stdio = subproceso
   local; la sesión es única y **stateful**.

## Datos oficiales que conviene recordar

- Un **client ⇄ un server** (relación 1:1 y dedicada). Varios servers ⇒ varios clients.
- El **inputSchema** de cada tool es JSON Schema; da validación y documentación al LLM.
- **Sampling** y **elicitation** son primitivos que el *server* puede pedirle al
  *client* (pedir una complet; pedir input/confirmación al usuario). Hoy no los usamos.
- Handshake: `initialize` (negocia `protocolVersion` + `capabilities`) →
  `notifications/initialized` → ya se puede `tools/list` / `tools/call`.

Fuentes:
- Arquitectura: https://modelcontextprotocol.io/docs/learn/architecture
- Construir cliente: https://modelcontextprotocol.io/docs/develop/build-client
- Best practices de cliente: https://modelcontextprotocol.io/docs/develop/clients/client-best-practices
