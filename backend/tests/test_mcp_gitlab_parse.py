from app.services.mcp_gitlab import MCPGitLabClient


def test_parse_tool_result_empty_content_returns_empty_list():
    client = MCPGitLabClient()
    response = {"result": {"content": [], "isError": False}}

    assert client._parse_tool_result(response) == []
