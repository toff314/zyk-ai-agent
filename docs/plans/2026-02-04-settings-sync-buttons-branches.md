# Settings Sync Buttons & GitLab Branch Count Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add “同步数据” buttons to MySQL/GitLab config tabs, and ensure GitLab project branch counts are synced (all projects) when syncing.

**Architecture:** Add backend sync endpoints that reuse config-stored credentials and call existing sync services, extending GitLab sync to include branch sync for all projects. Frontend adds API wrappers and buttons in Settings to trigger sync with feedback; branch counts will update after sync (via cached branches table).

**Tech Stack:** FastAPI + SQLAlchemy (async), Vue 3 + Element Plus, Vitest, Pytest.

---

### Task 1: Backend tests for new sync endpoints (@test-driven-development)

**Files:**
- Create: `backend/tests/test_config_sync_endpoints.py`

**Step 1: Write the failing test**

Create `backend/tests/test_config_sync_endpoints.py`:

```python
import json
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.config import Config
from app.api.config import sync_gitlab_data, sync_mysql_data


@pytest.fixture
async def async_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


async def seed_gitlab_config(session):
    session.add(
        Config(
            key="gitlab_config",
            value=json.dumps({"url": "http://gitlab", "token": "t", "groups": "g"}),
        )
    )
    await session.commit()


async def seed_mysql_config(session):
    session.add(
        Config(
            key="mysql_config",
            value=json.dumps({
                "enabled": True,
                "host": "localhost",
                "port": 3306,
                "user": "u",
                "password": "p",
                "database": "db",
                "timeout": 60,
            }),
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_sync_gitlab_data_uses_saved_config(monkeypatch, async_session):
    await seed_gitlab_config(async_session)

    async def fake_sync_users(db, config, client=None):
        return {"success": True, "user_count": 1}

    async def fake_sync_projects(db, config, client=None):
        return {"success": True, "project_count": 2}

    async def fake_sync_branches(db, config):
        return {"success": True, "branch_count": 3}

    monkeypatch.setattr("app.api.config.sync_gitlab_users", fake_sync_users)
    monkeypatch.setattr("app.api.config.sync_gitlab_projects", fake_sync_projects)
    monkeypatch.setattr("app.api.config.sync_all_gitlab_branches", fake_sync_branches)

    result = await sync_gitlab_data(db=async_session, current_user=type("U", (), {"role": "admin"})())

    assert result["code"] == 0
    assert "同步成功" in result["sync"]["message"]


@pytest.mark.asyncio
async def test_sync_mysql_data_uses_saved_config(monkeypatch, async_session):
    await seed_mysql_config(async_session)

    async def fake_sync_mysql(db, config):
        return {"database_count": 1, "table_count": 2}

    monkeypatch.setattr("app.api.config.sync_mysql_metadata", fake_sync_mysql)

    result = await sync_mysql_data(db=async_session, current_user=type("U", (), {"role": "admin"})())

    assert result["code"] == 0
    assert "同步成功" in result["sync"]["message"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && /home/yuanwu/zyk-ai-agent/backend/venv/bin/python -m pytest tests/test_config_sync_endpoints.py -v`
Expected: FAIL (missing endpoints + helpers).

---

### Task 2: Backend implementation of sync endpoints + branch sync (@test-driven-development)

**Files:**
- Modify: `backend/app/api/config.py`
- Modify: `backend/app/services/gitlab_sync.py`

**Step 1: Write minimal implementation**

1) In `backend/app/services/gitlab_sync.py`, add helper to sync branches for all projects:

```python
async def sync_all_gitlab_branches(db: AsyncSession, gitlab_config: dict) -> dict:
    projects = (await db.execute(select(GitLabProject))).scalars().all()
    total = 0
    for project in projects:
        result = await sync_gitlab_branches(db, gitlab_config, project.id)
        total += result.get("branch_count", 0)
    return {"success": True, "branch_count": total}
```

2) In `backend/app/api/config.py`, add two new endpoints:

```python
@router.post("/sync/gitlab")
async def sync_gitlab_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # admin check
    # load gitlab_config from Config, parse JSON
    # validate groups
    # call sync_gitlab_users + sync_gitlab_projects + sync_all_gitlab_branches
    # return {code, message, sync}
```

```python
@router.post("/sync/mysql")
async def sync_mysql_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # admin check
    # load mysql_config from Config, parse JSON
    # ensure enabled
    # call sync_mysql_metadata
    # return {code, message, sync}
```

3) Update `update_gitlab_config` to include branch sync and message update:

```python
branch_result = await sync_all_gitlab_branches(db, {...})
# message includes branch_count
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && /home/yuanwu/zyk-ai-agent/backend/venv/bin/python -m pytest tests/test_config_sync_endpoints.py -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add backend/app/api/config.py backend/app/services/gitlab_sync.py backend/tests/test_config_sync_endpoints.py
git commit -m "feat: add config sync endpoints and branch sync"
```

---

### Task 3: Frontend API tests for sync endpoints (@test-driven-development)

**Files:**
- Create: `frontend/src/api/config.test.ts`

**Step 1: Write the failing test**

Create `frontend/src/api/config.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { syncGitLabData, syncMySQLData } from './config'

const { postMock } = vi.hoisted(() => ({ postMock: vi.fn() }))

vi.mock('@/utils/request', () => {
  return {
    default: {
      get: vi.fn(),
      put: vi.fn(),
      post: postMock
    }
  }
})

beforeEach(() => {
  postMock.mockReset()
})

describe('config sync api', () => {
  it('calls gitlab sync endpoint', async () => {
    postMock.mockResolvedValue({ code: 0 })
    await syncGitLabData()
    expect(postMock).toHaveBeenCalledWith('/config/sync/gitlab')
  })

  it('calls mysql sync endpoint', async () => {
    postMock.mockResolvedValue({ code: 0 })
    await syncMySQLData()
    expect(postMock).toHaveBeenCalledWith('/config/sync/mysql')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL (functions missing).

---

### Task 4: Frontend sync buttons and API wiring (@test-driven-development)

**Files:**
- Modify: `frontend/src/api/config.ts`
- Modify: `frontend/src/views/Settings.vue`

**Step 1: Implement API functions**

Add to `frontend/src/api/config.ts`:

```ts
export async function syncGitLabData(): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.post('/config/sync/gitlab')
}

export async function syncMySQLData(): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.post('/config/sync/mysql')
}
```

**Step 2: Add buttons and handlers in Settings**

- Add `syncingMysql` / `syncingGitlab` refs.
- Add new buttons next to 测试连接 / 保存配置.
- On click, call `syncMySQLData()` / `syncGitLabData()` and show success/warn messages same style as save.

**Step 3: Run tests**

Run: `cd frontend && npm test`
Expected: PASS.

**Step 4: Commit**

```bash
git add frontend/src/api/config.ts frontend/src/views/Settings.vue frontend/src/api/config.test.ts
git commit -m "feat: add mysql/gitlab sync buttons"
```

---

### Task 5: Verification (@verification-before-completion)

**Step 1: Backend tests**

Run:

```bash
cd backend
/home/yuanwu/zyk-ai-agent/backend/venv/bin/python -m pytest tests/test_config_sync_endpoints.py -v
```

**Step 2: Frontend tests**

Run:

```bash
cd frontend
npm test
```

**Step 3: Manual check**

- Settings → GitLab配置 / MySQL配置：点击“同步数据”成功提示
- GitLab管理：项目列表 `分支数` 应在同步后显示非 0（若项目存在分支）

---

## Notes
- Sync branch counts requires syncing branches for every project; can be slow on large instances.
- If needed, add progress logging on backend.
