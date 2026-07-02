from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from chatbot.config import settings

# Usamos el motor asíncrono con aiomysql
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Cambia a True si quieres ver el SQL en la consola
    pool_size=10,
    max_overflow=20,
)

# Fábrica de sesiones para usar en el MCP
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
