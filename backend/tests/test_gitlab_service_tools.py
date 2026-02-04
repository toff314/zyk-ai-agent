import asyncio

from app.config.settings import settings
from app.services.gitlab import GitLabService


class StubClient:
    async def list_projects(self, _config):
        return [{"id": 1, "name": "proj"}]

    async def list_users(self, _config):
        return [{"id": 2, "username": "alice"}]

    async def list_branches(self, _config, project_id):
        return [{"name": f"main-{project_id}"}]

    async def list_commits(self, _config, project_id, limit=20, ref_name=None):
        return [{"id": f"{project_id}-{limit}-{ref_name}"}]


def _make_service():
    settings.GITLAB_TOKEN = "dummy-token"
    service = GitLabService()
    service.client = StubClient()
    return service


def test_list_projects_uses_mcp_client():
    service = _make_service()

    result = asyncio.run(service.list_projects())

    assert result == [{"id": 1, "name": "proj"}]


def test_list_users_uses_mcp_client():
    service = _make_service()

    result = asyncio.run(service.list_users())

    assert result == [{"id": 2, "username": "alice"}]


def test_list_branches_uses_mcp_client():
    service = _make_service()

    result = asyncio.run(service.list_branches(5))

    assert result == [{"name": "main-5"}]


def test_list_commits_uses_mcp_client():
    service = _make_service()

    result = asyncio.run(service.list_commits(7, limit=3, ref_name="dev"))

    assert result == [{"id": "7-3-dev"}]
