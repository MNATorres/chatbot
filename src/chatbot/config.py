from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Definimos la variable y su tipo
    DATABASE_URL: str = "mysql+aiomysql://root:password@127.0.0.1:3306/employees"
    
    # Esto le dice a Pydantic que busque en un archivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Aquí creamos la instancia que el error no encontraba
settings = Settings()