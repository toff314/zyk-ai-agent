import pytest

from app.models.gitlab_user import GitLabUser
from app.models.gitlab_project import GitLabProject
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.services.gitlab_sync import sync_gitlab_users, sync_gitlab_projects
from app.services.mysql_sync import sync_mysql_metadata


class StubGitLabClient:
    async def list_users(self, _config):
        return [
            {"id": 1, "username": "alice", "name": "Alice", "avatar_url": "u1"},
            {"id": 2, "username": "bob", "name": "Bob", "avatar_url": "u2"},
        ]

    async def list_projects(self, _config):
        return [
            {
                "id": 11,
                "name_with_namespace": "group/app-1",
                "path_with_namespace": "group/app-1",
                "web_url": "https://gitlab/group/app-1",
                "last_activity_at": "2024-01-01",
            },
            {
                "id": 12,
                "name_with_namespace": "group/app-2",
                "path_with_namespace": "group/app-2",
                "web_url": "https://gitlab/group/app-2",
                "last_activity_at": "2024-01-02",
            },
        ]


class StubMySQLClient:
    async def list_databases(self, _config):
        return [
            {"database": "information_schema"},
            {"database": "app_db"},
        ]

    async def list_tables(self, database, _config):
        if database == "app_db":
            return [
                {"table_name": "users", "table_type": "BASE TABLE", "table_comment": ""},
                {"table_name": "orders", "table_type": "BASE TABLE", "table_comment": ""},
            ]
        return []


class StubSession:
    def __init__(self):
        self.added = []
        self.executed = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_sync_gitlab_users_inserts():
    session = StubSession()
    result = await sync_gitlab_users(session, {"url": "x", "token": "y"}, client=StubGitLabClient())
    assert result["user_count"] == 2

    rows = [obj for obj in session.added if isinstance(obj, GitLabUser)]
    assert len(rows) == 2
    assert {r.username for r in rows} == {"alice", "bob"}
    assert all(r.commits_week == 0 for r in rows)


@pytest.mark.asyncio
async def test_sync_mysql_metadata_filters_system_db():
    session = StubSession()
    result = await sync_mysql_metadata(session, {"host": "h"}, client=StubMySQLClient())
    assert result["database_count"] == 1
    assert result["table_count"] == 2

    db_rows = [obj for obj in session.added if isinstance(obj, MySQLDatabase)]
    assert [r.name for r in db_rows] == ["app_db"]

    table_rows = [obj for obj in session.added if isinstance(obj, MySQLTable)]
    assert {r.table_name for r in table_rows} == {"users", "orders"}


@pytest.mark.asyncio
async def test_sync_gitlab_projects_inserts():
    session = StubSession()
    result = await sync_gitlab_projects(session, {"url": "x", "token": "y"}, client=StubGitLabClient())
    assert result["project_count"] == 2

    rows = [obj for obj in session.added if isinstance(obj, GitLabProject)]
    assert len(rows) == 2
    assert {r.path_with_namespace for r in rows} == {"group/app-1", "group/app-2"}
