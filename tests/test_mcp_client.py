"""Tests de `MCPClientManager`: mapeo de tools tras initialize y delegación
de call_tool a la sesión MCP."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from chatbot.mcp_client import MCPClientManager


async def test_initialize_mapea_las_tools():
    session = MagicMock()
    session.initialize = AsyncMock()
    tools = [
        SimpleNamespace(name="query_production_db", description="lee la db", inputSchema={"type": "object"}),
        SimpleNamespace(name="list_discord_channels", description="canales", inputSchema={}),
    ]
    session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=tools))

    client = MCPClientManager(session)
    await client.initialize()

    session.initialize.assert_awaited_once()
    assert [t["name"] for t in client.tools] == ["query_production_db", "list_discord_channels"]
    assert client.tools[0] == {
        "name": "query_production_db",
        "description": "lee la db",
        "input_schema": {"type": "object"},
    }


async def test_call_tool_delega_en_la_sesion():
    session = MagicMock()
    session.call_tool = AsyncMock(return_value="ok")

    client = MCPClientManager(session)
    res = await client.call_tool("query_production_db", {"sql": "SELECT 1"})

    assert res == "ok"
    session.call_tool.assert_awaited_once_with("query_production_db", arguments={"sql": "SELECT 1"})
