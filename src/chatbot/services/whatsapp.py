import httpx
from loguru import logger

from chatbot.config import settings


async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """Envía un mensaje de texto de WhatsApp a un usuario mediante la Cloud API de Meta"""

    access_token = settings.WHATSAPP_TOKEN
    phone_id = settings.WHATSAPP_PHONE_ID

    # --- FIX PARA NÚMEROS DE ARGENTINA (ZONA 11) EN MODO PRUEBA DE META ---
    # Bug del sandbox: FB guarda tu número como 541115... (con el 15 local)
    # pero el webhook entrante dice 54911... (internacional). Solo aplica en el
    # sandbox: en producción rompería números legítimos, por eso va tras un flag.
    if settings.WHATSAPP_SANDBOX and phone_number.startswith("54911"):
        phone_number = phone_number.replace("54911", "541115", 1)

    # URL oficial de la API de WhatsApp
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{phone_id}/messages"

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # Forma del mensaje (texto plano de envio normal)
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }

    async with httpx.AsyncClient() as client:
        try:
            # Mandar la respuesta hacia Meta
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"✅ Respuesta enviada por WhatsApp a {phone_number}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Error al enviar mensaje por WhatsApp (Status {e.response.status_code}): {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"❌ Error interno de red mandando WhatsApp: {str(e)}")
            return False
