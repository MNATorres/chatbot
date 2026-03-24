from sqlalchemy import text
from chatbot.mcp_server import mcp
from chatbot.database import SessionLocal

@mcp.tool()
async def query_production_db(sql: str) -> str:
    """
    Ejecuta una consulta SQL de lectura en la base de datos de producción.
    Úsala para obtener métricas, conteos o detalles de empleados.
    """
    # Forzamos que solo sean consultas SELECT por seguridad
    if not sql.strip().upper().startswith("SELECT"):
        return "Error: Solo se permiten consultas de lectura (SELECT)."

    async with SessionLocal() as session:
        result = await session.execute(text(sql))
        # Obtenemos los nombres de las columnas y las filas
        columns = result.keys()
        rows = result.fetchall()
        
        if not rows:
            return "No se encontraron resultados."

        # Formateamos el resultado de forma amigable para la IA
        data = [dict(zip(columns, row)) for row in rows]
        return str(data)