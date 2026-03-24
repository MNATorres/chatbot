from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Definimos la variable y su tipo
    DATABASE_URL: str = "mysql+aiomysql://root:password@127.0.0.1:3306/employees"
    PORT: int = 8000
    DEBUG: bool = True
    ANTHROPIC_API_KEY: Optional[str] = None
    WHATSAPP_TOKEN: Optional[str] = None
    
    # Esto le dice a Pydantic que busque en un archivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Aquí creamos la instancia que el error no encontraba
settings = Settings()