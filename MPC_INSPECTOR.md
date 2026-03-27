# 🚀 Guía de Pruebas: MCP Inspector

Para validar que el Especialista en Datos (MCP Server) está funcionando correctamente y puede consultar los 300,024 registros de la base de datos, sigue estos pasos:

## 1. Preparación de la Terminal

Abre una terminal en la raíz del proyecto (`C:\Users\matia\...\chatbot`) y ejecuta el siguiente comando para iniciar el entorno de desarrollo del Model Context Protocol:

```powershell
$env:PYTHONPATH = "src"; uv run mcp dev src/chatbot/mcp_server.py
```

Esto configurará el entorno y abrirá automáticamente una pestaña en tu navegador con el MCP Inspector.

## 2. Configuración en el Navegador (Inspector UI)

Una vez en la web del Inspector, asegúrate de que los campos de conexión tengan los siguientes valores para que el cliente encuentre tu código:

- **Command**: `uv`
- **Arguments**: `run python src/chatbot/mcp_server.py`
- **Environment Variables**:
  - Haz clic en "Add Environment Variable".
  - **Name**: `PYTHONPATH`
  - **Value**: `src`

> **Nota**: No borres las variables automáticas de Windows (PATH, USERNAME, etc.), solo añade la de `PYTHONPATH`.

## 3. Conexión y Validación de Herramientas

1. Haz clic en el botón **Connect**. El indicador debe ponerse en Verde (Connected).
2. Dirígete a la pestaña **Tools** en la parte superior.
3. Presiona el botón **List**. Debería aparecer la herramienta: `query_production_db`.

## 4. Consultas de Prueba (SQL)

Selecciona la herramienta `query_production_db` y ejecuta estas consultas en el campo `sql` para verificar la salud del sistema:

| Objetivo | Consulta SQL | Resultado Esperado |
| :--- | :--- | :--- |
| **Conteo Total** | `SELECT count(*) FROM employees;` | `[{"count(*)": 300024}]` |
| **Top Salarios** | `SELECT e.first_name, e.last_name, s.salary FROM employees e JOIN salaries s ON e.emp_no = s.emp_no WHERE s.to_date = '9999-01-01' ORDER BY s.salary DESC LIMIT 5;` | Lista de los 5 empleados con mejores sueldos actuales. |

## 🛠 Solución de Problemas Comunes

- **Error EPIPE o ModuleNotFoundError**: Revisa que el `PYTHONPATH` en el navegador esté configurado como `src`.
- **Error de Conexión a DB**: Verifica que el contenedor de Docker con MySQL esté encendido (`docker ps`).
- **Lista de Tools vacía**: Asegúrate de que el archivo `mcp_server.py` tenga la línea `import chatbot.tools.db_tools` al final.
