from sqlalchemy import text
from chatbot.database import SessionLocal
from chatbot.app import mcp  # Neutral

@mcp.tool()
async def query_production_db(sql: str) -> str:
    """Ejecuta una consulta SQL SELECT en la base de datos de producción."""
    if not sql.strip().upper().startswith("SELECT"):
        return "Error: Solo se permiten consultas SELECT."

    async with SessionLocal() as session:
        result = await session.execute(text(sql))
        rows = result.fetchall()
        
        if not rows:
            return "No se encontraron resultados."
        
        # Mapping convierte las filas en diccionarios para la IA
        return str([dict(row._mapping) for row in rows])