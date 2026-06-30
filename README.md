<div align="center">

# 🤖 Chatbot Hub

### Un agente de IA conversacional impulsado por **Claude** y el **Model Context Protocol (MCP)**

Un backend que conecta un modelo de lenguaje con tus datos y canales de mensajería
(MySQL, WhatsApp y Discord) mediante un ciclo de razonamiento autónomo (ReAct).

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-1.26+-blueviolet.svg)](https://modelcontextprotocol.io/)
[![Claude](https://img.shields.io/badge/Claude-Anthropic-D97757.svg?logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![uv](https://img.shields.io/badge/uv-package%20manager-261230.svg?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

</div>

---

## 📖 ¿Qué es esto?

**Chatbot Hub** es un servidor que actúa como _host_ de un agente de IA. Recibe mensajes
de lenguaje natural desde distintos canales (una API HTTP, WhatsApp o Discord), se los
entrega a **Claude**, y le da acceso a un conjunto de **herramientas (tools)** publicadas a
través del **Model Context Protocol**.

El modelo decide de forma autónoma qué herramientas usar —consultar la base de datos,
leer o enviar mensajes en Discord, etc.— en un **bucle de razonamiento ReAct** hasta
construir una respuesta final, que luego se devuelve al canal de origen.

```
   Usuario                          Backend (FastAPI)                       Herramientas
 ┌─────────┐   POST /ask        ┌────────────────────────┐
 │  HTTP   │ ─────────────────► │                        │
 ├─────────┤   webhook Meta     │      routes.py         │
 │WhatsApp │ ─────────────────► │          │             │
 ├─────────┤   gateway WS       │          ▼             │
 │ Discord │ ─────────────────► │    ChatbotHost         │
 └─────────┘                    │  (bucle ReAct, Claude) │
                                │          │             │
                                │          ▼             │
                                │   MCPClientManager  ◄──┼──── stdio ───┐
                                └────────────────────────┘              │
                                                                        ▼
                                                          ┌──────────────────────────┐
                                                          │   mcp_server.py (FastMCP) │
                                                          │   ├─ query_production_db  │──► 🗄️ MySQL
                                                          │   ├─ list_discord_channels│──► 🎮 Discord
                                                          │   ├─ read_channel_messages│
                                                          │   └─ send_message_to_...  │
                                                          └──────────────────────────┘
```

---

## ✨ Características

- 🧠 **Agente autónomo (ReAct)** — Claude razona en hasta 10 iteraciones, encadenando
  llamadas a herramientas hasta resolver la consulta.
- 🔌 **Arquitectura MCP desacoplada** — las herramientas viven en un **subproceso MCP
  independiente** que se comunica por `stdio`, separando el cerebro (host) de las capacidades.
- 🗄️ **Consultas a base de datos en lenguaje natural** — el modelo traduce preguntas a SQL
  de **solo lectura**, con validación estricta (lista blanca de comandos + lista negra de
  palabras peligrosas).
- 📱 **Multicanal** — un mismo cerebro responde por **API REST**, **WhatsApp** (Meta Cloud
  API) y **Discord**.
- ⚡ **100% asíncrono** — FastAPI + SQLAlchemy async + aiomysql + httpx, sin bloquear el
  event loop.
- 🐳 **Entorno reproducible** — MySQL y phpMyAdmin listos vía Docker Compose, con la base
  de ejemplo `employees` (~300.000 registros).

---

## 🏗️ Arquitectura del Código

El proyecto sigue el patrón **Host → Client → Server** del Model Context Protocol, donde el
servidor de herramientas corre como un proceso aparte.

```text
chatbot/
├── src/chatbot/
│   ├── main.py              # 🚀 App FastAPI + CORS; lifespan que inyecta cliente MCP y host
│   ├── routes.py            # 🛣️  Endpoints HTTP (/ask, health, webhooks de WhatsApp)
│   ├── mcp_host.py          # 🧠 ChatbotHost: bucle de razonamiento ReAct con Claude
│   ├── mcp_client.py        # 🔗 MCPClientManager: levanta y habla con el servidor MCP por stdio
│   ├── mcp_server.py        # 🔌 Punto de entrada del servidor MCP (registra las tools)
│   ├── app.py               # ⚙️  Instancia FastMCP + lifespan de la base de datos
│   ├── config.py            # 🔐 Settings tipados con Pydantic (lee variables de entorno)
│   ├── database.py          # 🗄️  Engine async de SQLAlchemy + fábrica de sesiones
│   ├── services/            # 📡 Conectores externos
│   │   ├── discord_service.py  #   🎮 Cliente de Discord (login, leer/enviar, listar canales)
│   │   └── whatsapp.py         #   📱 Envío de mensajes vía Meta Cloud API
│   └── tools/               # 🧰 Herramientas expuestas al modelo vía MCP
│       ├── db_tools.py         #   📊 query_production_db (SQL de solo lectura validado)
│       ├── discord_tools.py    #   🎮 Enviar / leer / listar canales de Discord
│       └── rag_tools.py        #   🧠 (Reservado para RAG — aún no implementado)
├── docker/mysql/init/       # 🐳 Scripts SQL de inicialización (base de ejemplo employees)
├── docker-compose.yml       # 🐳 MySQL 8.0 + phpMyAdmin
├── pyproject.toml           # 📦 Dependencias y script `start`
└── MPC_INSPECTOR.md         # 🔍 Guía para depurar las tools con el MCP Inspector
```

### Flujo de una petición

1. Un mensaje llega por `POST /ask` o por el webhook de WhatsApp en [`routes.py`](src/chatbot/routes.py).
2. La ruta delega en **`ChatbotHost.process_message`** ([`mcp_host.py`](src/chatbot/mcp_host.py)).
3. El host le envía el mensaje a **Claude** junto con la lista de herramientas disponibles.
4. Si Claude pide usar una tool, el host la ejecuta a través del **`MCPClientManager`**
   ([`mcp_client.py`](src/chatbot/mcp_client.py)), que reenvía la llamada al subproceso
   **`mcp_server.py`** por `stdio`.
5. El resultado vuelve al modelo, que razona de nuevo. El ciclo se repite hasta que Claude
   produce una respuesta de texto final.
6. La respuesta se devuelve por el mismo canal (JSON HTTP o mensaje de WhatsApp).

---

## 🛠️ Stack Tecnológico

| Tecnología | Rol en el proyecto |
| :--- | :--- |
| **[Claude (Anthropic)](https://www.anthropic.com/)** | Modelo de lenguaje que razona y decide qué herramientas usar. |
| **[Model Context Protocol](https://modelcontextprotocol.io/)** | Estándar que conecta el agente con las herramientas (vía `FastMCP`). |
| **[FastAPI](https://fastapi.tiangolo.com/)** + **[Uvicorn](https://www.uvicorn.org/)** | Servidor web asíncrono de alto rendimiento y los endpoints HTTP. |
| **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** + **[aiomysql](https://github.com/aio-libs/aiomysql)** | ORM y driver async para hablar con MySQL sin bloquear. |
| **[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** | Carga y validación tipada de la configuración (`.env`). |
| **[discord.py](https://discordpy.readthedocs.io/)** | Cliente para leer y enviar mensajes en Discord. |
| **[httpx](https://www.python-httpx.org/)** | Cliente HTTP async para la Meta Cloud API de WhatsApp. |
| **[uv](https://docs.astral.sh/uv/)** | Gestor de paquetes y entornos ultrarrápido. |
| **[Docker](https://www.docker.com/)** | MySQL 8.0 + phpMyAdmin para desarrollo local. |

---

## 🚀 Puesta en Marcha

### 1. Requisitos previos

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (`pip install uv` si aún no lo tienes)
- **Docker** (para la base de datos local)
- Una **API key de Anthropic**

### 2. Instalar dependencias

```bash
uv sync
```

`uv` lee `pyproject.toml` / `uv.lock` y crea el entorno virtual con las versiones exactas.

### 3. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```dotenv
# Base de datos (coincide con docker-compose.yml)
DATABASE_URL="mysql+aiomysql://root:password@127.0.0.1:3306/employees"

# Inteligencia artificial
ANTHROPIC_API_KEY="sk-ant-..."

# WhatsApp (Meta Cloud API) — opcional
WHATSAPP_TOKEN="..."
WHATSAPP_PHONE_ID="..."
WHATSAPP_VERIFY_TOKEN="..."

# Discord — opcional
DISCORD_TOKEN="..."
```

### 4. Levantar la base de datos

```bash
docker compose up -d
```

Esto inicia **MySQL 8.0** (puerto `3306`) con la base de ejemplo `employees` y
**phpMyAdmin** en [http://localhost:8080](http://localhost:8080).

### 5. Arrancar el servidor

```bash
uv run start
```

La API queda disponible en [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 📡 Endpoints HTTP

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Health check; indica si el cliente MCP está conectado. |
| `POST` | `/ask` | Envía un mensaje al agente. Body: `{ "message": "..." }`. |
| `GET` | `/webhook/whatsapp` | Verificación del webhook por parte de Meta. |
| `POST` | `/webhook/whatsapp` | Recepción de mensajes entrantes de WhatsApp. |

**Ejemplo:**

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cuáles son los 5 empleados con mayor salario actual?"}'
```

```json
{ "answer": "Los empleados con mayor salario actual son ..." }
```

---

## 🔍 Depurar las herramientas (MCP Inspector)

Para inspeccionar y probar las tools de forma aislada (sin pasar por Claude), consulta
[`MPC_INSPECTOR.md`](MPC_INSPECTOR.md). En resumen:

```powershell
$env:PYTHONPATH = "src"; uv run mcp dev src/chatbot/mcp_server.py
```

---

## 🗺️ Roadmap

- [ ] Implementar **RAG** (búsqueda vectorial / contextual) en [`rag_tools.py`](src/chatbot/tools/rag_tools.py).
- [ ] Persistir el historial de conversación por usuario (hoy cada mensaje es _stateless_).
- [ ] Tests automatizados sobre el host y las herramientas.

---

<div align="center">
  <sub>Diseñado con ❤️ para la automatización conversacional delegada a Agentes Inteligentes.</sub>
</div>
