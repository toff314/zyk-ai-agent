# GitLab & MySQL MCP Config Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add GitLab test-connection + post-save user sync via MCP, unify MySQL sync to use MCP tools, and refactor for reuse/maintainability.

**Architecture:** Introduce reusable sync helpers for GitLab/MySQL that accept an MCP client and update local cache tables. Config endpoints call these helpers and return sync results. MySQL metadata refresh uses the same MCP-backed helpers. Frontend uses new API calls for GitLab test + sync, and Settings UI mirrors MySQL flow. GitLab MCP server returns avatar_url for user sync.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy Async, fastmcp, python-gitlab, Vue 3, Element Plus, pytest.

---

### Task 1: Add failing tests for MCP sync helpers

**Files:**
- Create: `backend/tests/test_config_sync.py`

**Step 1: Write the failing test**

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.models.database import Base
from app.models.gitlab_user import GitLabUser
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.services.gitlab_sync import sync_gitlab_users
from app.services.mysql_sync import sync_mysql_metadata


class StubGitLabClient:
    async def list_users(self, _config):
        return [
            {"id": 1, "username": "alice", "name": "Alice", "avatar_url": "u1"},
            {"id": 2, "username": "bob", "name": "Bob", "avatar_url": "u2"},
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


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_gitlab_users_inserts(db_session):
    result = await sync_gitlab_users(db_session, {"url": "x", "token": "y"}, client=StubGitLabClient())
    assert result["user_count"] == 2

    rows = (await db_session.execute(select(GitLabUser))).scalars().all()
    assert len(rows) == 2
    assert {r.username for r in rows} == {"alice", "bob"}
    assert all(r.commits_week == 0 for r in rows)


@pytest.mark.asyncio
async def test_sync_mysql_metadata_filters_system_db(db_session):
    result = await sync_mysql_metadata(db_session, {"host": "h"}, client=StubMySQLClient())
    assert result["database_count"] == 1
    assert result["table_count"] == 2

    db_rows = (await db_session.execute(select(MySQLDatabase))).scalars().all()
    assert [r.name for r in db_rows] == ["app_db"]

    table_rows = (await db_session.execute(select(MySQLTable))).scalars().all()
    assert {r.table_name for r in table_rows} == {"users", "orders"}
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_config_sync.py -v`
Expected: FAIL (missing sync helpers).

**Step 3: Write minimal implementation**

```python
# backend/app/services/gitlab_sync.py
import logging
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gitlab_user import GitLabUser
from app.models.database import safe_commit
from app.services.mcp_gitlab import MCPGitLabClient

logger = logging.getLogger(__name__)


async def sync_gitlab_users(db: AsyncSession, gitlab_config: dict, client: MCPGitLabClient | None = None) -> dict:
    client = client or MCPGitLabClient()
    users = await client.list_users(gitlab_config)

    await db.execute(delete(GitLabUser))
    for user in users:
        db.add(
            GitLabUser(
                id=user.get("id"),
                username=user.get("username"),
                name=user.get("name"),
                avatar_url=user.get("avatar_url"),
                commits_week=0,
                commits_month=0,
            )
        )
    await safe_commit(db)

    return {"success": True, "user_count": len(users)}
```

```python
# backend/app/services/mysql_sync.py
import logging
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.models.database import safe_commit
from app.services.mcp_mysql import MCPMySQLClient

logger = logging.getLogger(__name__)
SYSTEM_DATABASES = {"information_schema", "performance_schema", "mysql", "sys"}


async def sync_mysql_databases(db: AsyncSession, mysql_config: dict, client: MCPMySQLClient | None = None) -> list[dict]:
    client = client or MCPMySQLClient()
    databases = await client.list_databases(mysql_config)

    await db.execute(delete(MySQLDatabase))
    for item in databases:
        name = item.get("database") or item.get("Database")
        if not name or name in SYSTEM_DATABASES:
            continue
        db.add(MySQLDatabase(name=name))
    await safe_commit(db)
    return databases


async def sync_mysql_tables(db: AsyncSession, mysql_config: dict, database: str, client: MCPMySQLClient | None = None) -> list[dict]:
    client = client or MCPMySQLClient()
    tables = await client.list_tables(database, mysql_config)

    await db.execute(delete(MySQLTable).where(MySQLTable.database_name == database))
    for item in tables:
        db.add(
            MySQLTable(
                database_name=database,
                table_name=item.get("table_name") or "",
                table_type=item.get("table_type") or "",
                table_comment=item.get("table_comment") or "",
            )
        )
    await safe_commit(db)
    return tables


async def sync_mysql_metadata(db: AsyncSession, mysql_config: dict, client: MCPMySQLClient | None = None) -> dict:
    client = client or MCPMySQLClient()
    databases = await sync_mysql_databases(db, mysql_config, client=client)

    user_dbs = [
        d.get("database") or d.get("Database")
        for d in databases
        if (d.get("database") or d.get("Database")) not in SYSTEM_DATABASES
    ]

    table_count = 0
    for db_name in user_dbs:
        if not db_name:
            continue
        tables = await sync_mysql_tables(db, mysql_config, db_name, client=client)
        table_count += len(tables)

    return {"success": True, "database_count": len(user_dbs), "table_count": table_count}
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_config_sync.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/gitlab_sync.py backend/app/services/mysql_sync.py backend/tests/test_config_sync.py
git commit -m "test: add sync helper coverage"
```

### Task 2: Add MCP GitLab client and wire config + chat + mysql metadata

**Files:**
- Create: `backend/app/services/mcp_gitlab.py`
- Modify: `backend/app/api/config.py`
- Modify: `backend/app/api/mysql_metadata.py`
- Modify: `backend/app/api/chat.py`

**Step 1: Write the failing test**

```python
# extend backend/tests/test_config_sync.py
@pytest.mark.asyncio
async def test_sync_gitlab_users_handles_empty(db_session):
    class EmptyClient:
        async def list_users(self, _config):
            return []

    result = await sync_gitlab_users(db_session, {"url": "x"}, client=EmptyClient())
    assert result["user_count"] == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_config_sync.py -v`
Expected: FAIL until gitlab_sync handles empty + MCP client exists.

**Step 3: Write minimal implementation**

```python
# backend/app/services/mcp_gitlab.py
import subprocess
import sys
import json
import mcp.types as mcp_types
from typing import Optional, Any
from pathlib import Path
import logging
import select
import time

logger = logging.getLogger(__name__)


class MCPGitLabClient:
    def __init__(self):
        backend_root = Path(__file__).resolve().parents[2]
        self.server_path = str(backend_root / "mcp-server" / "gitlab-mcp-server" / "server.py")
        self._request_id = 0

    def _build_env(self, gitlab_config: Optional[dict[str, Any]] = None) -> dict[str, str]:
        env = {}
        if gitlab_config:
            env.update({
                "GITLAB_URL": gitlab_config.get("url", ""),
                "GITLAB_TOKEN": gitlab_config.get("token", ""),
            })
        return env

    def _call_tool(self, name: str, arguments: Optional[dict[str, Any]], gitlab_config: Optional[dict[str, Any]] = None):
        # same JSON-RPC stdio flow as MCPMySQLClient
        ...

    def _parse_tool_result(self, response: dict[str, Any]):
        ...

    async def list_users(self, gitlab_config: Optional[dict[str, Any]] = None):
        return self._call_tool("list_users", {}, gitlab_config=gitlab_config)
```

```python
# backend/app/api/config.py (gitlab + mysql updates)
from app.services.gitlab_sync import sync_gitlab_users
from app.services.mysql_sync import sync_mysql_metadata
from app.services.mcp_gitlab import MCPGitLabClient

@router.put("/gitlab")
async def update_gitlab_config(...):
    ...
    sync_result = {"success": True, "message": "同步成功"}
    try:
        result = await sync_gitlab_users(db, {"url": config_data.url, "token": config_data.token})
        sync_result["message"] = f"同步成功: {result['user_count']} 个用户"
    except Exception as sync_error:
        sync_result = {"success": False, "message": f"同步失败: {sync_error}"}

    return {"code": 1 if not sync_result["success"] else 0, "message": "GitLab配置更新成功", "sync": sync_result}


@router.post("/test/gitlab")
async def test_gitlab_config(...):
    client = MCPGitLabClient()
    users = await client.list_users({"url": config_data.url, "token": config_data.token})
    return {"code": 0, "message": "GitLab连接测试成功", "data": {"user_count": len(users)}}


@router.put("/mysql")
async def update_mysql_config(...):
    ...
    try:
        result = await sync_mysql_metadata(db, mysql_config)
        sync_result["message"] = f"同步成功: {result['database_count']} 个数据库, {result['table_count']} 个表"
    except Exception as sync_error:
        sync_result = {"success": False, "message": f"同步失败: {sync_error}"}
```

```python
# backend/app/api/mysql_metadata.py
from app.services.mysql_sync import sync_mysql_databases, sync_mysql_tables

async def _sync_databases(db: AsyncSession, mysql_config: dict) -> list[dict]:
    return await sync_mysql_databases(db, mysql_config)

async def _sync_tables(db: AsyncSession, mysql_config: dict, database: str) -> list[dict]:
    return await sync_mysql_tables(db, mysql_config, database)
```

```python
# backend/app/api/chat.py
from app.models.gitlab_user import GitLabUser
from sqlalchemy import select

@router.get("/gitlab/users")
async def get_gitlab_users(...):
    result = await db.execute(select(GitLabUser).order_by(GitLabUser.name.asc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "avatar_url": u.avatar_url,
            "commits_week": u.commits_week,
            "commits_month": u.commits_month,
        }
        for u in users
    ]
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_config_sync.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/mcp_gitlab.py backend/app/api/config.py backend/app/api/mysql_metadata.py backend/app/api/chat.py

git commit -m "feat: add gitlab test/sync via mcp and unify mysql sync"
```

### Task 3: Update GitLab MCP server to return avatar_url

**Files:**
- Modify: `backend/mcp-server/gitlab-mcp-server/server.py`
- Modify: `backend/mcp-server/gitlab-mcp-server/tests/test_tools.py`

**Step 1: Write the failing test**

```python
# in test_list_users
    users = [
        StubUser(10, "Alice", "alice", "active"),
    ]
    users[0].avatar_url = "https://gitlab/avatar"

    ...
    assert result == [
        {"id": 10, "name": "Alice", "username": "alice", "state": "active", "avatar_url": "https://gitlab/avatar"}
    ]
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: FAIL until avatar_url included.

**Step 3: Write minimal implementation**

```python
@mcp.tool()
def list_users():
    ...
    return [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "state": user.state,
            "avatar_url": getattr(user, "avatar_url", None),
        }
        for user in users
    ]
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/mcp-server/gitlab-mcp-server/server.py backend/mcp-server/gitlab-mcp-server/tests/test_tools.py

git commit -m "feat: include gitlab avatar in mcp list_users"
```

### Task 4: Update frontend GitLab config flow

**Files:**
- Modify: `frontend/src/api/config.ts`
- Modify: `frontend/src/views/Settings.vue`

**Step 1: Write the failing test**

N/A (no frontend test harness in repo). Confirm behavior manually after implementation.

**Step 2: Write minimal implementation**

```ts
// frontend/src/api/config.ts
export async function testGitLabConfig(config: GitLabConfig): Promise<{ code: number; message: string; data?: { user_count: number } }> {
  return request.post('/config/test/gitlab', config)
}

export async function updateGitLabConfigWithSync(config: GitLabConfig): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.put('/config/gitlab', config)
}
```

```vue
// frontend/src/views/Settings.vue
// add testingGitlab ref and handleTestGitlabConfig()
// add test button in GitLab tab
// update saveGitlabConfig() to show sync message like MySQL
```

**Step 3: Manual verify**

- Click “测试连接” in GitLab config and confirm success/error message.
- Click “保存配置” and confirm sync result message appears.

**Step 4: Commit**

```bash
git add frontend/src/api/config.ts frontend/src/views/Settings.vue

git commit -m "feat: add gitlab test + sync UI"
```
