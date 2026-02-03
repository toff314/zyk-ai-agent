# MySQL Config Test + Metadata Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a MySQL "test connection" button in Settings and ensure saving MySQL config triggers immediate metadata sync (databases/tables) with sync-failure feedback.

**Architecture:** The config save endpoint will upsert `mysql_config`, then call a shared sync helper that refreshes `mysql_databases` and `mysql_tables` via MCP. Response includes sync status and counts; frontend shows success or warning. A new MySQL test endpoint will call MCP without mutating metadata.

**Tech Stack:** FastAPI, SQLAlchemy (async), Pydantic, Vue 3, Element Plus, Axios, Vitest

---

### Task 1: Add MCPMySQLClient.test_connection (backend)

**Files:**
- Modify: `backend/tests/test_mcp_mysql.py`
- Modify: `backend/app/services/mcp_mysql.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_mcp_mysql.py`:

```python
from unittest.mock import AsyncMock

class TestMCPMySQLClient:
    @patch.object(MCPMySQLClient, 'list_databases', new_callable=AsyncMock)
    def test_test_connection_calls_list_databases(self, mock_list_databases, mcp_client):
        mock_list_databases.return_value = [{"database": "db1"}]

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                mcp_client.test_connection(mysql_config={"host": "localhost"})
            )
            assert result is True
            mock_list_databases.assert_called_once_with(mysql_config={"host": "localhost"})
        finally:
            loop.close()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_mcp_mysql.py::TestMCPMySQLClient::test_test_connection_calls_list_databases -v`

Expected: FAIL with `AttributeError: 'MCPMySQLClient' object has no attribute 'test_connection'`.

**Step 3: Write minimal implementation**

Modify `backend/app/services/mcp_mysql.py`:

```python
    async def test_connection(self, mysql_config: Optional[dict[str, Any]] = None) -> bool:
        await self.list_databases(mysql_config=mysql_config)
        return True
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_mcp_mysql.py::TestMCPMySQLClient::test_test_connection_calls_list_databases -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_mcp_mysql.py backend/app/services/mcp_mysql.py
git commit -m "test: add mysql test_connection coverage"
```

---

### Task 2: Sync MySQL metadata on save + unit tests

**Files:**
- Create: `backend/tests/test_mysql_config_sync.py`
- Modify: `backend/app/api/mysql_metadata.py`
- Modify: `backend/app/api/config.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_mysql_config_sync.py`:

```python
import asyncio
import json
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.config import MySQLConfigRequest, apply_mysql_config
from app.api.mysql_metadata import sync_mysql_metadata
from app.models.config import Config
from app.models.database import Base
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _make_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, sessionmaker


@patch("app.api.mysql_metadata.mcp_mysql_client.list_databases", new_callable=AsyncMock)
@patch("app.api.mysql_metadata.mcp_mysql_client.list_tables", new_callable=AsyncMock)
def test_sync_mysql_metadata_inserts_rows(mock_list_tables, mock_list_databases):
    mock_list_databases.return_value = [
        {"Database": "db1"},
        {"database": "db2"}
    ]
    mock_list_tables.side_effect = [
        [{"table_name": "t1", "table_type": "BASE TABLE", "table_comment": "c1"}],
        [{"TABLE_NAME": "t2", "TABLE_TYPE": "VIEW", "TABLE_COMMENT": "c2"}]
    ]

    async def run():
        engine, sessionmaker = await _make_session()
        async with sessionmaker() as db:
            result = await sync_mysql_metadata(db, {"host": "localhost"})
            assert result["databases"] == 2
            assert result["tables"] == 2

            db_result = await db.execute(select(MySQLDatabase).order_by(MySQLDatabase.name.asc()))
            names = [row.name for row in db_result.scalars().all()]
            assert names == ["db1", "db2"]

            table_result = await db.execute(
                select(MySQLTable)
                .order_by(MySQLTable.database_name.asc(), MySQLTable.table_name.asc())
            )
            tables = table_result.scalars().all()
            assert [(t.database_name, t.table_name) for t in tables] == [
                ("db1", "t1"),
                ("db2", "t2")
            ]
        await engine.dispose()

    _run(run())


@patch("app.api.config.sync_mysql_metadata", new_callable=AsyncMock)
def test_apply_mysql_config_sync_failure_returns_sync_false(mock_sync):
    mock_sync.side_effect = Exception("sync failed")
    config_data = MySQLConfigRequest(
        host="localhost",
        port=3306,
        user="root",
        password="pwd",
        database="db1"
    )

    async def run():
        engine, sessionmaker = await _make_session()
        async with sessionmaker() as db:
            response = await apply_mysql_config(db, config_data)
            assert response["code"] == 0
            assert response["sync"]["success"] is False
            assert "sync failed" in response["sync"]["message"]

            result = await db.execute(select(Config).where(Config.key == "mysql_config"))
            config = result.scalar_one()
            value = json.loads(config.value)
            assert value["host"] == "localhost"
            assert value["enabled"] is True
        await engine.dispose()

    _run(run())


@patch("app.api.config.sync_mysql_metadata", new_callable=AsyncMock)
def test_apply_mysql_config_sync_success_returns_counts(mock_sync):
    mock_sync.return_value = {"databases": 1, "tables": 3}
    config_data = MySQLConfigRequest(
        host="localhost",
        port=3306,
        user="root",
        password="pwd",
        database="db1"
    )

    async def run():
        engine, sessionmaker = await _make_session()
        async with sessionmaker() as db:
            response = await apply_mysql_config(db, config_data)
            assert response["code"] == 0
            assert response["sync"]["success"] is True
            assert response["sync"]["databases"] == 1
            assert response["sync"]["tables"] == 3
        await engine.dispose()

    _run(run())
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_mysql_config_sync.py -v`

Expected: FAIL with missing `sync_mysql_metadata` and `apply_mysql_config`.

**Step 3: Write minimal implementation (sync helper)**

Modify `backend/app/api/mysql_metadata.py`:

```python
async def sync_mysql_metadata(db: AsyncSession, mysql_config: dict) -> dict:
    databases = await _sync_databases(db, mysql_config)
    database_names = []
    for item in databases:
        name = item.get("database") or item.get("Database")
        if name:
            database_names.append(name)

    total_tables = 0
    for database in database_names:
        tables = await _sync_tables(db, mysql_config, database)
        total_tables += len(tables)

    return {"databases": len(database_names), "tables": total_tables}
```

**Step 4: Write minimal implementation (apply + response)**

Modify `backend/app/api/config.py`:

```python
from app.api.mysql_metadata import sync_mysql_metadata


async def apply_mysql_config(db: AsyncSession, config_data: MySQLConfigRequest) -> dict:
    result = await db.execute(select(Config).where(Config.key == "mysql_config"))
    config = result.scalar_one_or_none()

    config_value = {
        "host": config_data.host,
        "port": config_data.port,
        "user": config_data.user,
        "password": config_data.password,
        "database": config_data.database,
        "enabled": True,
        "timeout": 60
    }

    if config:
        config.value = json.dumps(config_value)
    else:
        config = Config(key="mysql_config", value=json.dumps(config_value))
        db.add(config)

    await safe_commit(db)
    await db.refresh(config)

    sync_info = {"success": True}
    try:
        sync_result = await sync_mysql_metadata(db, config_value)
        sync_info.update(sync_result)
    except Exception as e:
        logger.error(f"同步MySQL元数据失败: {str(e)}")
        sync_info = {"success": False, "message": str(e)}

    return {
        "code": 0,
        "message": "MySQL配置更新成功",
        "sync": sync_info
    }
```

Update the endpoint to call the helper:

```python
@router.put("/mysql")
async def update_mysql_config(...):
    if current_user.role != "admin":
        ...
    try:
        return await apply_mysql_config(db, config_data)
    except Exception as e:
        await db.rollback()
        ...
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_mysql_config_sync.py -v`

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/app/api/config.py backend/app/api/mysql_metadata.py backend/tests/test_mysql_config_sync.py
git commit -m "feat: sync mysql metadata on config save"
```

---

### Task 3: Add MySQL test endpoint + unit tests

**Files:**
- Modify: `backend/app/api/config.py`
- Create: `backend/tests/test_mysql_connection.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mysql_connection.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch

from app.api.config import MySQLConfigRequest, perform_mysql_connection_test


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@patch("app.api.config.mcp_mysql_client.test_connection", new_callable=AsyncMock)
def test_perform_mysql_connection_test_success(mock_test):
    mock_test.return_value = True
    config_data = MySQLConfigRequest(
        host="localhost",
        port=3306,
        user="root",
        password="pwd",
        database="db1"
    )

    result = _run(perform_mysql_connection_test(config_data))
    assert result["code"] == 0
    assert "成功" in result["message"]
    mock_test.assert_called_once()


@patch("app.api.config.mcp_mysql_client.test_connection", new_callable=AsyncMock)
def test_perform_mysql_connection_test_failure(mock_test):
    mock_test.side_effect = Exception("boom")
    config_data = MySQLConfigRequest(
        host="localhost",
        port=3306,
        user="root",
        password="pwd",
        database="db1"
    )

    result = _run(perform_mysql_connection_test(config_data))
    assert result["code"] == -1
    assert "boom" in result["message"]
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_mysql_connection.py -v`

Expected: FAIL with missing `perform_mysql_connection_test`.

**Step 3: Write minimal implementation**

Modify `backend/app/api/config.py`:

```python
from app.services.mcp_mysql import mcp_mysql_client


async def perform_mysql_connection_test(config_data: MySQLConfigRequest) -> dict:
    mysql_config = {
        "host": config_data.host,
        "port": config_data.port,
        "user": config_data.user,
        "password": config_data.password,
        "database": config_data.database
    }
    try:
        await mcp_mysql_client.test_connection(mysql_config=mysql_config)
        return {"code": 0, "message": "MySQL连接测试成功"}
    except Exception as e:
        logger.error(f"测试MySQL连接失败: {str(e)}")
        return {"code": -1, "message": f"测试失败: {str(e)}"}
```

Add the new endpoint:

```python
@router.post("/test/mysql")
async def test_mysql_config(
    config_data: MySQLConfigRequest,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(...)

    return await perform_mysql_connection_test(config_data)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_mysql_connection.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/api/config.py backend/tests/test_mysql_connection.py
git commit -m "feat: add mysql connection test endpoint"
```

---

### Task 4: Add frontend test harness + failing test

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/views/__tests__/Settings.mysql.test.ts`

**Step 1: Add Vitest config and dependencies**

Modify `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "@vue/test-utils": "^2.4.4",
    "jsdom": "^24.0.0",
    "typescript": "^5.4.2",
    "vite": "^5.1.6",
    "vitest": "^1.4.0",
    "vue-tsc": "^2.0.6"
  }
}
```

Create `frontend/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'element-plus': path.resolve(__dirname, './node_modules/element-plus')
    }
  },
  test: {
    environment: 'jsdom',
    globals: true
  }
})
```

**Step 2: Write the failing test**

Create `frontend/src/views/__tests__/Settings.mysql.test.ts`:

```ts
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import Settings from '../Settings.vue'
import * as configApi from '@/api/config'

vi.mock('@/api/config', () => ({
  getConfig: vi.fn().mockResolvedValue({}),
  updateModelConfig: vi.fn(),
  updateMySQLConfig: vi.fn().mockResolvedValue({ code: 0, sync: { success: true } }),
  testModelConfig: vi.fn(),
  testMySQLConfig: vi.fn().mockResolvedValue({ code: 0, message: 'ok' })
}))

const stubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-tabs': { template: '<div><slot /></div>' },
  'el-tab-pane': { template: '<div><slot /></div>' },
  'el-form': { template: '<form><slot /></form>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-input': { template: '<input />' },
  'el-input-number': { template: '<input />' },
  'el-button': {
    template: '<button @click="$emit(\'click\')"><slot /></button>'
  }
}

describe('Settings MySQL', () => {
  it('renders test button and calls API', async () => {
    const wrapper = mount(Settings, { global: { stubs } })
    await flushPromises()

    // switch to mysql tab
    // script-setup refs are exposed as unwrapped values on wrapper.vm
    wrapper.vm.activeTab = 'mysql'
    await wrapper.vm.$nextTick()

    const buttons = wrapper.findAll('button')
    const testButton = buttons.find((btn) => btn.text().includes('测试连接'))
    expect(testButton).toBeTruthy()

    await testButton!.trigger('click')
    await flushPromises()

    expect(configApi.testMySQLConfig).toHaveBeenCalled()
  })
})
```

**Step 3: Run test to verify it fails**

Run: `cd frontend && npm test`

Expected: FAIL because `testMySQLConfig` is not yet exported/used and the button does not exist.

**Step 4: Commit**

```bash
git add frontend/package.json frontend/vitest.config.ts frontend/src/views/__tests__/Settings.mysql.test.ts
git commit -m "test: add vitest setup and mysql settings test"
```

---

### Task 5: Frontend API + UI changes (test-driven)

**Files:**
- Modify: `frontend/src/api/config.ts`
- Modify: `frontend/src/views/Settings.vue`

**Step 1: Implement minimal API helpers**

Modify `frontend/src/api/config.ts`:

```ts
export interface MySQLSyncInfo {
  success: boolean
  message?: string
  databases?: number
  tables?: number
}

export interface MySQLConfigSaveResponse {
  code: number
  message?: string
  sync?: MySQLSyncInfo
}

export interface MySQLTestResponse {
  code: number
  message?: string
}

export async function updateMySQLConfig(config: MySQLConfig): Promise<MySQLConfigSaveResponse> {
  return request.put('/config/mysql', config)
}

export async function testMySQLConfig(config: MySQLConfig): Promise<MySQLTestResponse> {
  return request.post('/config/test/mysql', config)
}
```

**Step 2: Implement UI changes to satisfy the test**

Modify `frontend/src/views/Settings.vue` (MySQL tab buttons + handlers):

```ts
import { getConfig, updateModelConfig, updateMySQLConfig, testModelConfig as apiTestModelConfig, testMySQLConfig, type ModelConfig, type MySQLConfig } from '@/api/config'

const mysqlTesting = ref(false)

const handleTestMysqlConfig = async () => {
  mysqlTesting.value = true
  try {
    const result = await testMySQLConfig(mysqlConfig)
    if (result.code === 0) {
      ElMessage.success('MySQL连接测试成功')
    } else {
      ElMessage.error(result.message || '测试失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '测试失败')
  } finally {
    mysqlTesting.value = false
  }
}

const saveMysqlConfig = async () => {
  saving.value = true
  try {
    const result = await updateMySQLConfig(mysqlConfig)
    if (result.sync && result.sync.success === false) {
      ElMessage.warning(`MySQL配置保存成功，但元数据同步失败：${result.sync.message || '未知原因'}`)
    } else {
      ElMessage.success('MySQL配置保存成功')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}
```

Update the MySQL form buttons (place test on the left):

```vue
<el-form-item>
  <el-button type="primary" @click="handleTestMysqlConfig" :loading="mysqlTesting">测试连接</el-button>
  <el-button type="success" @click="saveMysqlConfig" :loading="saving">保存配置</el-button>
</el-form-item>
```

**Step 3: Run tests to verify they pass**

Run: `cd frontend && npm test`

Expected: PASS.

**Step 4: Commit**

```bash
git add frontend/src/api/config.ts frontend/src/views/Settings.vue
git commit -m "feat: add mysql test button and sync feedback"
```

---

### Task 6: Backend + frontend integration check

**Files:**
- None (verification only)

**Step 1: Run backend tests**

Run: `cd backend && pytest tests/test_mcp_mysql.py tests/test_mysql_config_sync.py tests/test_mysql_connection.py -v`

Expected: PASS.

**Step 2: Run frontend tests**

Run: `cd frontend && npm test`

Expected: PASS.

**Step 3: Manual smoke check**

- Start backend + frontend
- Open Settings -> MySQL tab
- Click "测试连接" and verify success or error
- Click "保存配置" and verify success message; if sync fails, warning appears

---

Plan complete. Execution should happen in a dedicated worktree.
