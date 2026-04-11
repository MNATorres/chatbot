import os
from fastapi import APIRouter, Request, Body, Query, HTTPException
from chatbot.services.whatsapp import send_whatsapp_message

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

# 🔥 NUEVAS RUTAS DE WHATSAPP 🔥

@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """(PASO 1) Meta verifica que el Webhook nos pertenezca."""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        print("✅ Webhook verificado por Meta exitosamente")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Error de validación del webhook")

@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(request: Request):
    """(PASO 2) Meta nos reenvía los mensajes que tú envías desde el celular."""
    data = await request.json()
    
    try:
        # El formato de Meta tiene bastantes niveles adentro
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        # Ignoramos notificaciones de "mensaje enviado/entregado" (solo queremos el texto entrante)
        if "messages" in value:
            message = value["messages"][0]
            phone_number_sender = message["from"]  # Quien te escribió
            text_body = message["text"]["body"]    # Lo que te escribieron
            
            # -> Magia MCP: Procesamos el mensaje tal como lo hace /ask
            mcp_client = request.app.state.mcp_client
            mcp_host = request.app.state.mcp_host
            
            print(f"\n💬 MSJ de WhatsApp [{phone_number_sender}]: {text_body}")
            answer = await mcp_host.process_message(text_body, mcp_client)
            
            # -> Responder de vuelta hacia WhatsApp
            await send_whatsapp_message(phone_number_sender, answer)
            
    except (KeyError, IndexError) as e:
        # A veces Meta manda pings vacios, simplemente devolvemos OK
        pass
        
    return {"status": "ok"}
