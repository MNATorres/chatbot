# 🏛️ Arquitectura

Este documento detalla cómo está construido **Chatbot Hub** y cómo fluye una petición a
través del sistema. Los diagramas están en [Mermaid](https://mermaid.js.org/) y se renderizan
automáticamente en GitHub.

El proyecto implementa el patrón **Host → Client → Server** del
[Model Context Protocol](https://modelcontextprotocol.io/): el "cerebro" (host) que conversa
con Claude está **desacoplado** de las herramientas, que viven en un **proceso aparte** y se
comunican por `stdio`.

---

## 1. Vista de componentes

Cómo se relacionan los módulos y los servicios externos.

```mermaid
flowchart TB
    subgraph channels["📥 Canales de entrada"]
        http["Cliente HTTP<br/>(POST /ask)"]
        wa["WhatsApp<br/>(webhook Meta)"]
        dc["Discord"]
    end

    subgraph backend["⚙️ Backend FastAPI (proceso principal)"]
        routes["routes.py<br/><i>endpoints HTTP</i>"]
        host["mcp_host.py<br/><b>ChatbotHost</b><br/><i>bucle ReAct</i>"]
        client["mcp_client.py<br/><b>MCPClientManager</b>"]
        waSvc["services/whatsapp.py"]
    end

    subgraph mcp["🔌 Servidor MCP (subproceso · stdio)"]
        server["mcp_server.py<br/><b>FastMCP</b>"]
        dbTools["tools/db_tools.py<br/><i>query_production_db</i>"]
        dcTools["tools/discord_tools.py"]
        ragTools["tools/rag_tools.py<br/><i>(reservado)</i>"]
    end

    subgraph external["🌐 Servicios externos"]
        claude["🧠 Claude<br/>(API Anthropic)"]
        mysql[("🗄️ MySQL<br/>employees")]
        discordApi["🎮 Discord API"]
        metaApi["📱 Meta Cloud API"]
    end

    http --> routes
    wa --> routes
    dc -.-> host
    routes --> host
    host <-->|razona y pide tools| claude
    host --> client
    client <-->|stdio| server
    server --> dbTools
    server --> dcTools
    server --> ragTools
    dbTools --> mysql
    dcTools --> discordApi
    host --> waSvc
    waSvc --> metaApi

    classDef ext fill:#2d2d3a,stroke:#D97757,color:#fff
    class claude,mysql,discordApi,metaApi ext
```

---

## 2. Flujo de una petición (bucle ReAct)

Qué ocurre, paso a paso, cuando llega un mensaje. El host repite el ciclo
**"preguntar a Claude → ejecutar tools → devolver resultados"** hasta **10 veces** o hasta
que Claude responde con texto final.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant R as routes.py
    participant H as ChatbotHost
    participant C as Claude (Anthropic)
    participant M as MCPClientManager
    participant S as mcp_server.py
    participant DB as MySQL / Discord

    U->>R: POST /ask { message }
    R->>H: process_message(message, mcp_client)

    loop Hasta 10 iteraciones (ReAct)
        H->>C: messages + tools disponibles
        C-->>H: respuesta (texto y/o tool_use)

        alt Claude pide usar una herramienta
            H->>M: call_tool(nombre, argumentos)
            M->>S: invoca la tool por stdio
            S->>DB: ejecuta (SQL de solo lectura / acción)
            DB-->>S: filas / resultado
            S-->>M: contenido de la tool
            M-->>H: resultado (truncado si > 40k)
            Note over H,C: el resultado se agrega al contexto<br/>y se vuelve a consultar a Claude
        else Claude responde texto final
            H-->>R: respuesta final
        end
    end

    R-->>U: { answer }
```

---

## 3. Ciclo de vida (startup / shutdown)

El cliente MCP y el host se inicializan **una sola vez** al arrancar, mediante el `lifespan`
de FastAPI, y se reutilizan en cada petición a través de `app.state`.

```mermaid
flowchart LR
    start(["uv run start"]) --> uvicorn["Uvicorn levanta<br/>chatbot.main:app"]
    uvicorn --> lifespan["lifespan() de FastAPI"]
    lifespan --> spawn["get_mcp_client():<br/>lanza subproceso mcp_server.py"]
    spawn --> init["MCPClientManager.initialize()<br/>negocia capacidades + lista tools"]
    init --> state["Guarda mcp_client y<br/>ChatbotHost en app.state"]
    state --> ready(["✅ API lista en :8000"])
    ready -.->|al cerrar| dispose["engine.dispose()<br/>+ cierre del subproceso MCP"]

    classDef ok fill:#1f3a2d,stroke:#3fb950,color:#fff
    class ready ok
```

---

## Referencias

- Resumen general y puesta en marcha: [`README.md`](README.md)
- Convenciones y guía para desarrollar: [`CLAUDE.md`](CLAUDE.md)
- Depuración de las herramientas MCP: [`MPC_INSPECTOR.md`](MPC_INSPECTOR.md)
