import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Body
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN MCP ---
server_params = StdioServerParameters(
    command="uv",
    args=["run", "python", "src/chatbot/mcp_server.py"],
    env={**os.environ, "PYTHONPATH": "src"}
)

# Diccionario global para guardar la sesión del MCP y el cliente de IA
state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja la conexión con el servidor MCP al iniciar la API."""
    print("🚀 Iniciando conexión con el Especialista MCP...")
    
    # Abrimos el "puente" con el servidor de la DB
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Guardamos la sesión y el cliente de Claude en el estado global
            state["mcp_session"] = session
            state["anthropic"] = Anthropic()
            
            # Obtenemos las herramientas una vez al inicio
            tools_res = await session.list_tools()
            state["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                } for t in tools_res.tools
            ]
            
            print(f"✅ Conectado. Herramientas listas: {[t['name'] for t in state['tools']]}")
            yield
            # Al apagar la API, el 'async with' cierra todo automáticamente.
    print("🛑 Conexión MCP cerrada.")

app = FastAPI(title="Chatbot AI Backend", lifespan=lifespan)

# --- ENDPOINTS ---

@app.get("/")
async def health_check():
    return {"status": "online", "mcp_connected": "mcp_session" in state}

@app.post("/ask")
async def ask_ai(message: str = Body(..., embed=True)):
    client = state["anthropic"]
    session = state["mcp_session"]
    
    messages = [{"role": "user", "content": message}]
    
    # Bucle de hasta 10 intentos para permitir "pensamiento"
    for i in range(10):
        print(f"\n--- 🧠 Intento de Razonamiento #{i+1} ---")
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            tools=state["tools"],
            messages=messages
        )

        # LOG DE PENSAMIENTO: Aquí vemos qué dice Claude ANTES de actuar
        for block in response.content:
            if block.type == "text":
                print(f"💭 Claude piensa: {block.text}")
            if block.type == "tool_use":
                print(f"🛠️ Claude decide usar: {block.name}")
                print(f"📝 SQL generado: {block.input.get('sql')}")

        if response.stop_reason != "tool_use":
            return {"answer": response.content[0].text}

        # Ejecución de la herramienta
        tool_use = next(block for block in response.content if block.type == "tool_use")
        result = await session.call_tool(tool_use.name, arguments=tool_use.input)
        
        print(f"📊 Resultado de la DB: {result.content[0].text[:100]}...") # Mostramos solo el inicio para no saturar

        # Alimentamos el contexto para la siguiente vuelta
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result.content[0].text
            }]
        })

def start():
    import uvicorn
    uvicorn.run("chatbot.main:app", host="127.0.0.1", port=8000, reload=True)