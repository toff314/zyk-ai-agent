import asyncio
from unittest.mock import patch

from app.services.mcp_gitlab import MCPGitLabClient


class _StubResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _StubSession:
    def __init__(self, values):
        self._values = values

    async def execute(self, _stmt):
        return _StubResult(self._values)


async def _stub_get_db(values):
    yield _StubSession(values)


def test_get_user_commits_uses_db_project_ids():
    client = MCPGitLabClient()

    with patch("app.services.mcp_gitlab.get_db", return_value=_stub_get_db([1, 2])):  # type: ignore[return-value]
        with patch.object(MCPGitLabClient, "_call_tool", return_value=[] ) as mock_call:
            asyncio.run(client.get_user_commits(None, "alice", limit=5))

    args, _ = mock_call.call_args
    assert args[1]["project_ids"] == [1, 2]
