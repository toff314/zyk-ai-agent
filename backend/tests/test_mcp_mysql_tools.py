import asyncio
from unittest.mock import patch

from app.services.mcp_mysql import MCPMySQLClient


def _run(coro):
    return asyncio.run(coro)


@patch.object(MCPMySQLClient, "_call_tool")
def test_show_table_status_calls_tool(mock_call):
    client = MCPMySQLClient()
    mock_call.return_value = [{"Name": "orders"}]

    result = _run(client.show_table_status("db1"))

    mock_call.assert_called_once_with("show_table_status", {"database": "db1"}, mysql_config=None)
    assert result == [{"Name": "orders"}]


@patch.object(MCPMySQLClient, "_call_tool")
def test_get_table_indexes_calls_tool(mock_call):
    client = MCPMySQLClient()
    mock_call.return_value = [{"Key_name": "idx_order"}]

    result = _run(client.get_table_indexes("orders", "db1"))

    mock_call.assert_called_once_with(
        "get_table_indexes",
        {"table_name": "orders", "database": "db1"},
        mysql_config=None,
    )
    assert result == [{"Key_name": "idx_order"}]
