from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Definimos la variable y su tipo
    DATABASE_URL: str = "mysql+aiomysql://root:password@127.0.0.1:3306/employees"
    PORT: int = 8000
    DEBUG: bool = True
    ANTHROPIC_API_KEY: Optional[str] = None

    # --- WhatsApp (Meta Cloud API) ---
    WHATSAPP_TOKEN: Optional[str] = None          # Bearer token para enviar mensajes
    WHATSAPP_PHONE_ID: Optional[str] = None        # ID del número emisor
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None    # Token del handshake del webhook (GET)
    WHATSAPP_APP_SECRET: Optional[str] = None      # App Secret para validar la firma HMAC
    WHATSAPP_API_VERSION: str = "v25.0"            # Versión del Graph API
    WHATSAPP_SANDBOX: bool = False                 # Activa el fix de números AR del sandbox

    DISCORD_TOKEN: Optional[str] = None
    
    # Esto le dice a Pydantic que busque en un archivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Aquí creamos la instancia que el error no encontraba
settings = Settings()