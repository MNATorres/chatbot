import hashlib
import hmac
import json

from fastapi import APIRouter, Request, Body, Query, HTTPException, BackgroundTasks
from loguru import logger

from chatbot.config import settings
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

# 🔥 RUTAS DE WHATSAPP 🔥

def _firma_meta_valida(body: bytes, signature_header: str | None) -> bool:
    """Valida el header X-Hub-Signature-256 (HMAC-SHA256 del body con el App Secret).

    Sin esto, cualquiera que conozca la URL podría inyectar mensajes falsos y hacer
    que enviemos WhatsApps arbitrarios desde nuestra cuenta.
    """
    app_secret = settings.WHATSAPP_APP_SECRET
    if not app_secret:
        # Sin secreto configurado no podemos validar: rechazamos por seguridad.
        logger.warning("⚠️ WHATSAPP_APP_SECRET no configurado; se rechaza el webhook.")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    esperado = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    recibido = signature_header.split("=", 1)[1]
    # Comparación en tiempo constante para evitar timing attacks.
    return hmac.compare_digest(esperado, recibido)


async def _procesar_mensaje_whatsapp(mcp_host, mcp_client, sender: str, text_body: str):
    """Corre el bucle ReAct y responde por WhatsApp. Se ejecuta en background."""
    logger.info(f"💬 MSJ de WhatsApp [{sender}]: {text_body}")
    try:
        answer = await mcp_host.process_message(text_body, mcp_client)
        await send_whatsapp_message(sender, answer)
    except Exception:
        # No dejamos que una excepción del procesamiento se pierda en silencio.
        logger.exception(f"❌ Error procesando el mensaje de WhatsApp [{sender}]")


@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """(PASO 1) Meta verifica que el Webhook nos pertenezca."""
    verify_token = settings.WHATSAPP_VERIFY_TOKEN

    if (
        hub_mode == "subscribe"
        and verify_token is not None
        and hub_verify_token is not None
        and hmac.compare_digest(hub_verify_token, verify_token)
    ):
        logger.info("✅ Webhook verificado por Meta exitosamente")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Error de validación del webhook")


@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(request: Request, background_tasks: BackgroundTasks):
    """(PASO 2) Meta nos reenvía los mensajes entrantes.

    Responde 200 de inmediato y procesa en background: el bucle ReAct puede tardar
    decenas de segundos y Meta reintenta si no contestás rápido (respuestas duplicadas).
    """
    # Leemos el body crudo (necesario para validar la firma sobre los bytes exactos).
    body = await request.body()

    # 1. Firma de Meta: si no es válida, ni parseamos.
    if not _firma_meta_valida(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Firma inválida")

    # 2. Parseo del payload (el try envuelve SOLO el parseo, no el procesamiento).
    try:
        data = json.loads(body)
        value = data["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError, ValueError):
        # A veces Meta manda pings vacíos o formatos inesperados: devolvemos OK.
        return {"status": "ignored"}

    # Solo nos interesan mensajes entrantes (ignoramos "enviado/entregado").
    if "messages" not in value:
        return {"status": "ok"}

    message = value["messages"][0]
    message_id = message.get("id")
    sender = message.get("from")

    # 3. Deduplicación: Meta entrega "at least once", el mismo id puede repetirse.
    seen = request.app.state.whatsapp_seen_ids
    if message_id and message_id in seen:
        logger.info(f"↩️ Mensaje duplicado ignorado: {message_id}")
        return {"status": "ok"}
    if message_id:
        seen.append(message_id)

    # 4. Por ahora solo entendemos texto. Otros tipos: avisamos (en background).
    if message.get("type") != "text":
        if sender:
            background_tasks.add_task(
                send_whatsapp_message, sender, "Por ahora solo puedo entender mensajes de texto 🙏"
            )
        return {"status": "ok"}

    text_body = message["text"]["body"]

    # 5. Procesamos en background y contestamos 200 YA.
    background_tasks.add_task(
        _procesar_mensaje_whatsapp,
        request.app.state.mcp_host,
        request.app.state.mcp_client,
        sender,
        text_body,
    )
    return {"status": "ok"}
