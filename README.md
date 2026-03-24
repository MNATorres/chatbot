<div align="center">
  <h1>🤖 Chatbot Hub Architecture</h1>
  <p><em>Un moderno servidor de integraciones y herramientas impulsado por Model Context Protocol (MCP) y FastAPI</em></p>

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-1.26+-blueviolet.svg)](https://modelcontextprotocol.io/)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-blue)](https://docs.astral.sh/uv/)

</div>

---

## 🏗️ Arquitectura del Proyecto

Este proyecto está diseñado para ser modular, dinámico y escalable. Separa limpiamente la lógica de la base de datos, las herramientas inteligentes, los conectores de redes sociales y los endpoints.

<details open>
<summary><b>📂 Árbol de Directorios y Estructura</b></summary>
  
```text
chatbot/
├── main.py           # 🚀 Punto de entrada principal (Servidor FastAPI)
├── mcp_server.py     # 🔌 Servidor de Model Context Protocol (MCP)
├── config.py         # ⚙️ Configuraciones y variables de entorno centralizadas
├── database.py       # 🗄️ Conexión asíncrona a la Base de Datos
├── services/         # 📡 Integraciones y Conectores de Redes
│   ├── discord.py    #   🎮 Servicio de Bot para Discord
│   └── whatsapp.py   #   📱 Servicio de mensajería webhook para WhatsApp
└── tools/            # 🧰 Herramientas LLM / MCP
    ├── db_tools.py   #   📊 Herramientas de consulta a la Base de Datos
    └── rag_tools.py  #   🧠 Retrieval-Augmented Generation (Modelos de Búsqueda)
```
</details>

## 🧩 Componentes Principales

### 1. 🚀 Núcleo de la Aplicación

- **`main.py`**: Es el punto de arranque de la aplicación. Inicializa el servidor web utilizando **FastAPI** y **Uvicorn**, exponiendo y enrutando los conectores hacia los demás módulos de la arquitectura de manera asíncrona y eficiente.
- **`config.py`**: Carga y procesa de forma segura todas las variables de entorno necesarias para que ningún token o información sensible quede embebida en el código.

### 2. 🔌 Integración Inteligente (MCP)

- **`mcp_server.py`**: Levanta el servidor compatible con el **Model Context Protocol**. Facilita la comunicación estándar al permitir que un Modelo de Lenguaje Entorno (LLM) o un Agente use y entienda el contexto y herramientas propias del chatbot, estandarizando la experiencia.

### 3. 🗄️ Capa de Datos

- **`database.py`**: Inicialización del gestor relacional (ORM) usando **SQLAlchemy** junto con un motor completamente asíncrono (**aiomysql**), preparado para lidiar con el tráfico e historiales de los chats sin bloquear la aplicación.
- **Base de Datos de Prueba**: El entorno de desarrollo usa el esquema de prueba oficial de MySQL: [datacharmer/test_db](https://github.com/datacharmer/test_db), proporcionando datos realistas y complejos para las consultas del agente.

### 4. 🧰 Herramientas Asistenciales (Tools)

Aquí viven las funcionalidades o _skills_ expuestas que el agente cognitivo puede usar durante una conversación:

- **`db_tools.py`**: Provee interfaces limpias para obtener analíticas, historial o inyectar nuevos eventos provenientes de los clientes dentro de la base de datos.
- **`rag_tools.py`**: La piedra angular de las consultas guiadas. Implementa funciones para realizar Búsquedas Vectoriales o Contextuales de manera de darle bases firmes (RAG) de conocimiento a las respuestas del bot.

### 5. 📡 Servicios de Mensajería (Services)

El chatbot no tendría sentido si no puede comunicarse con los usuarios de manera transversal:

- **`discord.py`**: Contiene los clientes de red orientados a la conexión WebSockets de cara a eventos y servidores de Discord, interpretando comandos e intenciones de usuarios.
- **`whatsapp.py`**: Encargado de los webhooks de Meta, interpreta las cargas de los mensajes de WhatsApp Cloud API, permitiendo un flujo robusto de texto e imágenes directo al usuario donde esté.

---

## 🛠️ Stack Tecnológico

| Tecnología                 | Descripción                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| **FastAPI**                | Framework web súper veloz, fuertemente tipado en Python, responsable de los endpoints.          |
| **Model Context Protocol** | Estandarización de herramientas LLM para conectar rápidamente agentes genéricos al contexto.    |
| **SQLAlchemy Async**       | Potente Toolkit SQL, ejecutándose de manera de no bloqueante a través de Event loops de Python. |
| **uv**                     | Sistema ultrarrápido de empaquetado y gestión de entornos para Python.  |

---

## 📦 Dependencias del Proyecto

El proyecto requiere **Python 3.13+** y está cimentado usando las siguientes librerías y componentes clave:

- **[FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)**: Motor de peticiones web de alto rendimiento.
- **[MCP (Model Context Protocol)](https://modelcontextprotocol.io/)**: Protocolo estandarizado para la capa de comunicación y uso de herramientas para modelos de lenguaje.
- **[SQLAlchemy](https://www.sqlalchemy.org/) & [aiomysql](https://github.com/aio-libs/aiomysql)**: Interfaz de Acceso y Mapeo Objeto Relacional a base de datos usando Event Loops asíncronos.
- **[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) & [python-dotenv](https://saurabh-kumar.com/python-dotenv/)**: Herramientas integradas para una gestión estricta y segura de configuraciones ambientales y validación estática del entorno.

---

## 🚀 Guía de Instalación y Ejecución Rápidas

Dado su rendimiento insuperable, el proyecto ahora utiliza exclusivamente [uv](https://docs.astral.sh/uv/) como gestor de paquetes (en sustitución de Poetry).

### 1. Requisitos Previos

Si no tienes `uv` instalado a nivel de sistema, es recomendable instalarlo de manera global. Puedes hacerlo usando el instalador oficial o bien a través de pip:

```bash
pip install uv
```

*(Consulta la [documentación oficial de uv](https://docs.astral.sh/uv/getting-started/installation/) si prefieres usar comandos como curl o Homebrew).*

### 2. Sincronización del Entorno (Instalación)

Con la herramienta en tu sistema, la instalación local es inmediata. Sitúate en la raíz del proyecto y sincroniza el árbol de dependencias. 

La orden analizará `pyproject.toml` y emulará automáticamente las dependencias bloqueadas en `uv.lock` instalándolas en un entorno virtual efímero (o actualizándolas):

```bash
# Instalar las dependencias del proyecto de forma local
uv sync
```

### 3. Levantando el Servidor

Una vez instalado simplemente corre el script de inicio empaquetado que lanzará a nuestra app usando uvicorn para atajar tráfico:

```bash
# Inicializar la aplicación completa
uv run start
```

<div align="center">
  <br>
  <i>Diseñado con ❤️ para la modernidad y automatización delegada a Agentes Inteligentes.</i>
</div>
