from fastapi import APIRouter, Request, Body

router = APIRouter()

@router.get("/")
async def health_check(request: Request):
    """Verifica si el servidor HTTP responde y si el cliente MCP fue inicializado en el estado local."""
    return {"status": "online", "mcp_connected": hasattr(request.app.state, "mcp_client")}

@router.post("/ask")
async def ask_ai(request: Request, message: str = Body(..., embed=True)):
    """Punto único de entrada HTTP que delega el procesamiento de lenguaje natural al Host de IA."""
    # Obtenemos instancias preiniciadas desde el motor de FastAPI
    mcp_client = request.app.state.mcp_client
    mcp_host = request.app.state.mcp_host
    
    # ➡ RUTAS DELEGA AL HOST EL PROCESAMIENTO
    answer = await mcp_host.process_message(message, mcp_client)
    
    return {"answer": answer}
