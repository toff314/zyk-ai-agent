import asyncio
import logging
from unittest.mock import patch

from app.services.mcp_gitlab import MCPGitLabClient


def _run(coro):
    return asyncio.run(coro)


def test_get_user_commits_logs_empty_result(caplog):
    client = MCPGitLabClient()
    caplog.set_level(logging.WARNING, logger="app.services.mcp_gitlab")

    with patch.object(MCPGitLabClient, "_call_tool", return_value=[]):
        result = _run(client.get_user_commits(None, "yuanwu", limit=5))

    assert result == []
    assert "get_user_commits" in caplog.text
    assert "yuanwu" in caplog.text
