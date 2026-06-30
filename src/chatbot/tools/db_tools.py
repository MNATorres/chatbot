import re
from sqlalchemy import text
from chatbot.database import SessionLocal
from chatbot.app import mcp  # Neutral

@mcp.tool()
async def query_production_db(sql: str) -> str:
    """Ejecuta consultas de solo lectura en la base de datos de producción."""
    sql_upper = sql.strip().upper()
    
    # Permitir consultas que sirvan para exploración o lectura
    allowed_starts = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH")
    if not sql_upper.startswith(allowed_starts):
        return "Error: La consulta debe empezar con SELECT, SHOW, DESCRIBE, EXPLAIN o WITH."

    # Eliminamos el contenido entre comillas para evitar falsos positivos
    sql_no_strings = re.sub(r"'.*?'", "", sql_upper)
    sql_no_strings = re.sub(r'".*?"', "", sql_no_strings)
    
    # Lista estricta de palabras bloqueadas
    forbidden_words = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "CALL", "UPSERT", "MERGE"}
    
    # Obtenemos todas las palabras alfanuméricas usadas en el comando SQL
    words = set(re.findall(r'\b[A-Z]+\b', sql_no_strings))
    
    # Si alguna o más están dentro de las prohibidas, lo rechazamos
    if forbidden_words.intersection(words):
        return f"Error: Operación no permitida. La consulta contiene palabras prohibidas."

    async with SessionLocal() as session:
        result = await session.execute(text(sql))
        # Para evitar sobrecargar la memoria con queries tipo SELECT *
        rows = result.fetchmany(100)
        
        if not rows:
            return "No se encontraron resultados."
        
        # Mapping convierte las filas en diccionarios para la IA
        return str([dict(row._mapping) for row in rows])