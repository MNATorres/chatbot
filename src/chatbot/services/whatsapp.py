import os
import httpx

async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """Envía un mensaje de texto de WhatsApp a un usuario mediante la Cloud API de Meta"""
    
    access_token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    
    # --- FIX PARA NÚMEROS DE ARGENTINA (ZONA 11) EN MODO PRUEBA DE META ---
    # Bug del sandbox: FB guarda tu número como 541115... (con el 15 local)
    # pero el webhook entrante dice 54911... (internacional).
    if phone_number.startswith("54911"):
        phone_number = phone_number.replace("54911", "541115", 1)
        
    # URL oficial de la API de WhatsApp
    url = f"https://graph.facebook.com/v25.0/{phone_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Forma del mensaje (texto plano de envio normal)
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Mandar la respuesta hacia Meta
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            print(f"✅ Respuesta enviada por WhatsApp a {phone_number}")
            return True
        except httpx.HTTPStatusError as e:
            print(f"❌ Error al enviar mensaje por WhatsApp (Status {e.response.status_code}): {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Error interno de red mandando WhatsApp: {str(e)}")
            return False
