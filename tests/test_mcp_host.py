"""Tests del bucle ReAct de `ChatbotHost`: salida, tool use, paralelismo,
truncado por max_tokens y el límite de iteraciones."""

from unittest.mock import AsyncMock, MagicMock

from chatbot.mcp_host import ChatbotHost, MAX_TOKENS
from tests.conftest import anthropic_response, text_block, tool_use_block, tool_result


def _host(create_side_effect=None, create_return=None):
    """Construye un host con el cliente de Anthropic mockeado."""
    host = ChatbotHost()
    host.anthropic = MagicMock()
    if create_side_effect is not None:
        host.anthropic.messages.create = AsyncMock(side_effect=create_side_effect)
    else:
        host.anthropic.messages.create = AsyncMock(return_value=create_return)
    return host


def _mock_client(tool_output="resultado de la tool"):
    client = MagicMock()
    client.tools = [{"name": "query_production_db"}]
    client.call_tool = AsyncMock(return_value=tool_result(tool_output))
    return client


# --- Salida directa (sin tools) ---


async def test_respuesta_directa_sin_tools():
    host = _host(create_return=anthropic_response([text_block("Hola!")], "end_turn"))
    client = _mock_client()

    res = await host.process_message("hola", client)

    assert res == "Hola!"
    client.call_tool.assert_not_called()
    # Le mandó max_tokens correcto
    _, kwargs = host.anthropic.messages.create.call_args
    assert kwargs["max_tokens"] == MAX_TOKENS


# --- Truncado por max_tokens ---


async def test_max_tokens_agrega_aviso_de_truncado():
    host = _host(create_return=anthropic_response([text_block("texto cortado")], "max_tokens"))
    res = await host.process_message("dame 50 filas", _mock_client())

    assert res.startswith("texto cortado")
    assert "truncada por longitud" in res.lower()


# --- Tool use: un turno con tool, luego respuesta final ---


async def test_ejecuta_tool_y_devuelve_respuesta_final():
    turno1 = anthropic_response([tool_use_block("query_production_db", {"sql": "SELECT 1"})], "tool_use")
    turno2 = anthropic_response([text_block("Listo, aquí está")], "end_turn")
    host = _host(create_side_effect=[turno1, turno2])
    client = _mock_client()

    res = await host.process_message("consulta", client)

    assert res == "Listo, aquí está"
    client.call_tool.assert_awaited_once_with("query_production_db", arguments={"sql": "SELECT 1"})
    assert host.anthropic.messages.create.call_count == 2


# --- Varias tools en un mismo turno (paralelismo con gather) ---


async def test_varias_tools_en_un_turno():
    turno1 = anthropic_response(
        [
            tool_use_block("list_discord_channels", {}, block_id="a"),
            tool_use_block("query_production_db", {"sql": "SELECT 1"}, block_id="b"),
        ],
        "tool_use",
    )
    turno2 = anthropic_response([text_block("fin")], "end_turn")
    host = _host(create_side_effect=[turno1, turno2])
    client = _mock_client()

    res = await host.process_message("dos cosas", client)

    assert res == "fin"
    assert client.call_tool.await_count == 2


# --- Límite de 10 iteraciones ---


async def test_limite_de_iteraciones():
    # Claude pide tools indefinidamente => se corta a las 10 vueltas.
    siempre_tool = anthropic_response([tool_use_block("query_production_db", {"sql": "SELECT 1"})], "tool_use")
    host = _host(create_return=siempre_tool)
    client = _mock_client()

    res = await host.process_message("bucle", client)

    assert "límite de razonamiento" in res
    assert host.anthropic.messages.create.call_count == 10


# --- _run_tool: truncado a 40000 chars ---


async def test_run_tool_trunca_resultados_gigantes():
    host = ChatbotHost()
    host.anthropic = MagicMock()
    client = MagicMock()
    client.call_tool = AsyncMock(return_value=tool_result("x" * 50000))
    tu = tool_use_block("query_production_db", {"sql": "SELECT *"}, block_id="z")

    bloque = await host._run_tool(client, tu)

    assert bloque["tool_use_id"] == "z"
    assert bloque["content"].endswith("[TRUNCADO POR LONGITUD MÁXIMA ALCANZADA]")
    assert len(bloque["content"]) < 41000


async def test_run_tool_resultado_normal_intacto():
    host = ChatbotHost()
    host.anthropic = MagicMock()
    client = MagicMock()
    client.call_tool = AsyncMock(return_value=tool_result("data corta"))
    tu = tool_use_block("t", {}, block_id="id1")

    bloque = await host._run_tool(client, tu)

    assert bloque == {"type": "tool_result", "tool_use_id": "id1", "content": "data corta"}
