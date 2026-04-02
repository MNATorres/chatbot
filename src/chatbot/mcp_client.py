import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClientManager:
    """Encapsula la sesión de MCP para invocar herramientas en el subproceso servidor."""
    
    def __init__(self, session: ClientSession):
        self.session = session
        self.tools = []
        
    async def initialize(self):
        """Negocia las capacidades y extrae las herramientas del servidor."""
        await self.session.initialize()
        tools_res = await self.session.list_tools()
        self.tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            } for tool in tools_res.tools
        ]
        
    async def call_tool(self, name: str, arguments: dict):
        """Ejecuta una herramienta de MCP en el servidor y retorna el resultado."""
        return await self.session.call_tool(name, arguments=arguments)

@asynccontextmanager
async def get_mcp_client() -> AsyncGenerator[MCPClientManager, None]:
    """Levanta el subproceso mcp_server.py y devuelve el cliente inicializado."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "src/chatbot/mcp_server.py"],
        env={**os.environ, "PYTHONPATH": "src"}
    )
    
    # Aquí es donde se establece la Capa de Transporte y la Capa de Datos
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            client = MCPClientManager(session)
            await client.initialize()
            print(f"✅ Conectado al Subproceso MCP. Herramientas listas: {[t['name'] for t in client.tools]}")
            
            yield client
            
    print("🛑 Conexión MCP cerrada correctamente.")
