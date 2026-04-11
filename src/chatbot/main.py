from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Importamos exclusivamente los componentes independientes
from chatbot.mcp_client import get_mcp_client
from chatbot.mcp_host import ChatbotHost
from chatbot.routes import router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orquestador principal: levanta el cliente MCP y lo inyecta a la memoria global."""
    print("🚀 Levantando todo el ecosistema de la aplicación...")
    
    # Obtenemos la conexión con el servidor MCP
    async with get_mcp_client() as mcp_client:
        # Inyectamos instacias listas para usarse en las rutas HTTP
        app.state.mcp_client = mcp_client
        app.state.mcp_host = ChatbotHost()
        yield

# Configuracion central del FastAPI
app = FastAPI(title="Chatbot AI Backend", lifespan=lifespan)

# 🔥 Configuración CORS para permitir peticiones desde tu frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Permitimos Vite local
    allow_credentials=True,
    allow_methods=["*"], # Permitimos todos los metodos (GET, POST, etc)
    allow_headers=["*"], # Permitimos cualquier header
)

app.include_router(router)

def start():
    import uvicorn
    uvicorn.run("chatbot.main:app", host="127.0.0.1", port=8000, reload=True)