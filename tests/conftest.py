"""Fixtures y helpers compartidos por la suite de tests.

Todo se corre sin red ni base de datos real: las dependencias externas
(Anthropic, MySQL, Discord, Meta) se mockean.
"""

import os
from types import SimpleNamespace

# La construcción de AsyncAnthropic() lee esta env var; la fijamos antes de
# importar cualquier módulo del proyecto para que no falle en los tests.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


# --- Factories para simular respuestas de la API de Claude ---


def text_block(text: str):
    """Bloque de tipo 'text' de una respuesta de Claude."""
    return SimpleNamespace(type="text", text=text)


def tool_use_block(name: str, tool_input: dict, block_id: str = "tu_1"):
    """Bloque de tipo 'tool_use' (Claude pide ejecutar una tool)."""
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def anthropic_response(content: list, stop_reason: str):
    """Respuesta de `messages.create` con sus bloques y motivo de fin."""
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def tool_result(text: str):
    """Resultado de una tool MCP: array `content` con un bloque de texto."""
    return SimpleNamespace(content=[SimpleNamespace(text=text)])
