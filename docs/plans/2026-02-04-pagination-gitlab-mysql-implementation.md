# Pagination for GitLab/MySQL Lists Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add consistent page/page_size pagination (default 20) to GitLab users/projects/branches/commits and MySQL databases/tables (including manage endpoints) in both backend APIs and frontend lists.

**Architecture:** Backend introduces a small pagination utility and applies it to list queries using offset/limit and count; each API response returns `{ items, total, page, page_size }`. Frontend adds a reusable pagination composable and wires it into management tables/drawers, with API wrappers passing page and page_size.

**Tech Stack:** FastAPI + SQLAlchemy (async), Vue 3 + Element Plus, Vitest, Pytest.

---

### Task 1: Backend pagination utility (@test-driven-development)

**Files:**
- Create: `backend/app/utils/pagination.py`
- Create: `backend/tests/test_pagination_utils.py`

**Step 1: Write the failing test**

Create `backend/tests/test_pagination_utils.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import DeclarativeBase

from app.utils.pagination import paginate_query


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))


@pytest.mark.asyncio
async def test_paginate_query_returns_total_and_page_items():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        session.add_all([Item(name=f"item-{idx:02d}") for idx in range(1, 51)])
        await session.commit()

    async with Session() as session:
        query = select(Item).order_by(Item.id.asc())
        total, items = await paginate_query(session, query, page=2, page_size=10)

        assert total == 50
        assert len(items) == 10
        assert [item.name for item in items] == [f"item-{idx:02d}" for idx in range(11, 21)]

    await engine.dispose()


@pytest.mark.asyncio
async def test_paginate_query_out_of_range_returns_empty_items():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        session.add_all([Item(name=f"item-{idx:02d}") for idx in range(1, 21)])
        await session.commit()

    async with Session() as session:
        query = select(Item).order_by(Item.id.asc())
        total, items = await paginate_query(session, query, page=3, page_size=10)

        assert total == 20
        assert items == []

    await engine.dispose()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_pagination_utils.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.utils.pagination'`.

**Step 3: Write minimal implementation**

Create `backend/app/utils/pagination.py`:

```python
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


def get_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


async def paginate_query(
    db: AsyncSession,
    query: Select,
    page: int,
    page_size: int,
):
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one() or 0

    offset = get_offset(page, page_size)
    items_result = await db.execute(query.offset(offset).limit(page_size))
    items = items_result.scalars().all()
    return total, items
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_pagination_utils.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/utils/pagination.py backend/tests/test_pagination_utils.py
git commit -m "feat: add backend pagination helper"
```

---

### Task 2: GitLab list pagination tests (@test-driven-development)

**Files:**
- Create: `backend/tests/test_gitlab_pagination.py`

**Step 1: Write the failing test**

Create `backend/tests/test_gitlab_pagination.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.gitlab_user import GitLabUser
from app.models.gitlab_project import GitLabProject
from app.models.gitlab_branch import GitLabBranch
from app.models.gitlab_commit import GitLabCommit
from app.api.gitlab_manage import (
    list_gitlab_users,
    list_gitlab_projects,
    list_gitlab_branches,
    list_gitlab_commits,
)


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


async def seed_gitlab_users(session, count=25):
    session.add_all(
        [
            GitLabUser(username=f"user-{idx:02d}", name=f"User {idx:02d}")
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


async def seed_gitlab_projects(session, count=15):
    session.add_all(
        [
            GitLabProject(
                name=f"project-{idx:02d}",
                path_with_namespace=f"group/project-{idx:02d}",
            )
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


async def seed_gitlab_branches(session, project_id=1, count=25):
    session.add_all(
        [
            GitLabBranch(
                project_id=project_id,
                name=f"branch-{idx:02d}",
                commit_sha=f"sha-{idx:02d}",
            )
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


async def seed_gitlab_commits(session, project_id=1, branch="main", count=25):
    session.add_all(
        [
            GitLabCommit(
                project_id=project_id,
                branch=branch,
                commit_sha=f"commit-{idx:02d}",
                title=f"Commit {idx:02d}",
                author_name="Tester",
                created_at=f"2026-02-04T00:{idx:02d}:00Z",
            )
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_list_gitlab_users_paginates(async_session):
    await seed_gitlab_users(async_session, 25)

    result = await list_gitlab_users(
        include_disabled=True,
        page=2,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert [item["username"] for item in result["items"]] == [
        f"user-{idx:02d}" for idx in range(11, 21)
    ]


@pytest.mark.asyncio
async def test_list_gitlab_projects_paginates(async_session):
    await seed_gitlab_projects(async_session, 15)

    result = await list_gitlab_projects(
        include_disabled=True,
        page=2,
        page_size=5,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 15
    assert result["page"] == 2
    assert result["page_size"] == 5
    assert [item["path_with_namespace"] for item in result["items"]] == [
        f"group/project-{idx:02d}" for idx in range(6, 11)
    ]


@pytest.mark.asyncio
async def test_list_gitlab_branches_paginates(async_session):
    await seed_gitlab_branches(async_session, project_id=1, count=25)

    result = await list_gitlab_branches(
        project_id=1,
        refresh=False,
        page=3,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 3
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"branch-{idx:02d}" for idx in range(21, 26)
    ]


@pytest.mark.asyncio
async def test_list_gitlab_commits_paginates(async_session):
    await seed_gitlab_commits(async_session, project_id=1, branch="main", count=25)

    result = await list_gitlab_commits(
        project_id=1,
        branch="main",
        refresh=False,
        limit=50,
        page=1,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 1
    assert result["page_size"] == 10
    # created_at desc: latest is 25
    assert result["items"][0]["commit_sha"] == "commit-25"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_gitlab_pagination.py -v`
Expected: FAIL (list functions missing page/page_size and response fields).

---

### Task 3: Implement GitLab list pagination (@test-driven-development)

**Files:**
- Modify: `backend/app/api/gitlab_manage.py`

**Step 1: Write minimal implementation**

In `backend/app/api/gitlab_manage.py`:

1) Add imports:

```python
from app.utils.pagination import paginate_query, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
```

2) Update list endpoints to accept pagination params and use `paginate_query`.

Example for projects (apply same pattern to users/branches/commits):

```python
@router.get("/projects")
async def list_gitlab_projects(
    include_disabled: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(GitLabProject).order_by(GitLabProject.path_with_namespace.asc())
    if not include_disabled:
        query = query.where(GitLabProject.enabled.is_(True))

    total, items = await paginate_query(db, query, page, page_size)

    count_result = await db.execute(
        select(GitLabBranch.project_id, func.count()).group_by(GitLabBranch.project_id)
    )
    branch_counts = {row[0]: row[1] for row in count_result.all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "path_with_namespace": item.path_with_namespace,
                "web_url": item.web_url,
                "last_activity_at": item.last_activity_at,
                "remark": item.remark,
                "enabled": item.enabled,
                "branch_count": branch_counts.get(item.id, 0),
            }
            for item in items
        ],
    }
```

Apply to users:

```python
@router.get("/users")
async def list_gitlab_users(
    include_disabled: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(GitLabUser).order_by(GitLabUser.username.asc())
    if not include_disabled:
        query = query.where(GitLabUser.enabled.is_(True))

    total, users = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "remark": user.remark,
                "enabled": user.enabled,
                "commits_week": user.commits_week,
                "commits_month": user.commits_month,
            }
            for user in users
        ],
    }
```

Branches:

```python
@router.get("/branches")
async def list_gitlab_branches(
    project_id: int = Query(...),
    refresh: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gitlab_config = await _load_gitlab_config(db)
    if refresh:
        await sync_gitlab_branches(db, gitlab_config, project_id)

    query = (
        select(GitLabBranch)
        .where(GitLabBranch.project_id == project_id)
        .order_by(GitLabBranch.name.asc())
    )
    total, branches = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "name": branch.name,
                "commit_sha": branch.commit_sha,
                "committed_date": branch.committed_date,
            }
            for branch in branches
        ],
    }
```

Commits:

```python
@router.get("/commits")
async def list_gitlab_commits(
    project_id: int = Query(...),
    branch: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gitlab_config = await _load_gitlab_config(db)
    if refresh:
        await sync_gitlab_commits(db, gitlab_config, project_id, branch, limit=limit)

    query = (
        select(GitLabCommit)
        .where(
            GitLabCommit.project_id == project_id,
            GitLabCommit.branch == branch,
        )
        .order_by(GitLabCommit.created_at.desc())
    )
    total, commits = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "commit_sha": item.commit_sha,
                "title": item.title,
                "author_name": item.author_name,
                "created_at": item.created_at,
                "web_url": item.web_url,
            }
            for item in commits
        ],
    }
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_gitlab_pagination.py -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add backend/app/api/gitlab_manage.py backend/tests/test_gitlab_pagination.py
git commit -m "feat: paginate gitlab list endpoints"
```

---

### Task 4: MySQL list pagination tests (@test-driven-development)

**Files:**
- Create: `backend/tests/test_mysql_pagination.py`

**Step 1: Write the failing test**

Create `backend/tests/test_mysql_pagination.py`:

```python
import json
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.config import Config
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.api.mysql_metadata import (
    list_mysql_databases,
    list_mysql_tables,
    list_mysql_databases_manage,
    list_mysql_tables_manage,
)


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


async def seed_mysql_config(session):
    config = Config(
        key="mysql_config",
        value=json.dumps(
            {
                "enabled": True,
                "host": "",
                "port": 3306,
                "user": "",
                "password": "",
                "database": "",
                "timeout": 60,
            }
        ),
    )
    session.add(config)
    await session.commit()


async def seed_mysql_databases(session, count=25):
    session.add_all(
        [MySQLDatabase(name=f"db_{idx:02d}") for idx in range(1, count + 1)]
    )
    await session.commit()


async def seed_mysql_tables(session, database="db_01", count=25):
    session.add_all(
        [
            MySQLTable(database_name=database, table_name=f"table_{idx:02d}")
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_list_mysql_databases_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_databases(async_session, 25)

    result = await list_mysql_databases(
        refresh=False,
        include_disabled=True,
        page=2,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"db_{idx:02d}" for idx in range(11, 21)
    ]


@pytest.mark.asyncio
async def test_list_mysql_tables_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_tables(async_session, database="db_01", count=25)

    result = await list_mysql_tables(
        database="db_01",
        refresh=False,
        include_disabled=True,
        page=3,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 3
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"table_{idx:02d}" for idx in range(21, 26)
    ]


@pytest.mark.asyncio
async def test_list_mysql_databases_manage_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_databases(async_session, 25)
    await seed_mysql_tables(async_session, database="db_01", count=3)

    result = await list_mysql_databases_manage(
        refresh=False,
        include_disabled=True,
        page=1,
        page_size=5,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 1
    assert result["page_size"] == 5
    assert len(result["items"]) == 5


@pytest.mark.asyncio
async def test_list_mysql_tables_manage_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_tables(async_session, database="db_02", count=21)

    result = await list_mysql_tables_manage(
        database="db_02",
        refresh=False,
        include_disabled=True,
        page=2,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 21
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"table_{idx:02d}" for idx in range(11, 21)
    ]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_mysql_pagination.py -v`
Expected: FAIL (list functions missing page/page_size and response fields).

---

### Task 5: Implement MySQL list pagination (@test-driven-development)

**Files:**
- Modify: `backend/app/api/mysql_metadata.py`

**Step 1: Write minimal implementation**

In `backend/app/api/mysql_metadata.py`:

1) Add imports:

```python
from app.utils.pagination import paginate_query, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
```

2) Update list endpoints to accept pagination params and use `paginate_query`.

Example for databases (apply same pattern to tables/manage endpoints):

```python
@router.get("/databases")
async def list_mysql_databases(
    refresh: bool = Query(False),
    include_disabled: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    mysql_config = await _load_mysql_config(db)
    if refresh:
        await _sync_databases(db, mysql_config)

    query = select(MySQLDatabase).order_by(MySQLDatabase.name.asc())
    if not include_disabled:
        query = query.where(MySQLDatabase.enabled.is_(True))

    total, items = await paginate_query(db, query, page, page_size)

    if not items and total == 0:
        await _sync_databases(db, mysql_config)
        total, items = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "remark": item.remark,
                "enabled": item.enabled,
            }
            for item in items
        ],
    }
```

Apply to tables:

```python
@router.get("/tables")
async def list_mysql_tables(
    database: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    include_disabled: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    mysql_config = await _load_mysql_config(db)
    if refresh:
        await _sync_tables(db, mysql_config, database)

    query = (
        select(MySQLTable)
        .where(MySQLTable.database_name == database)
        .order_by(MySQLTable.table_name.asc())
    )
    if not include_disabled:
        query = query.where(MySQLTable.enabled.is_(True))

    total, items = await paginate_query(db, query, page, page_size)

    if not items and total == 0:
        await _sync_tables(db, mysql_config, database)
        total, items = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "database": item.database_name,
                "name": item.table_name,
                "type": item.table_type,
                "comment": item.table_comment,
                "remark": item.remark,
                "enabled": item.enabled,
            }
            for item in items
        ],
    }
```

Apply to manage databases:

```python
@router.get("/manage/databases")
async def list_mysql_databases_manage(
    refresh: bool = Query(False),
    include_disabled: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mysql_config = await _load_mysql_config(db)
    if refresh:
        await _sync_databases(db, mysql_config)

    query = select(MySQLDatabase).order_by(MySQLDatabase.name.asc())
    if not include_disabled:
        query = query.where(MySQLDatabase.enabled.is_(True))

    total, items = await paginate_query(db, query, page, page_size)

    count_result = await db.execute(
        select(MySQLTable.database_name, func.count()).group_by(MySQLTable.database_name)
    )
    counts = {row[0]: row[1] for row in count_result.all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "remark": item.remark,
                "enabled": item.enabled,
                "table_count": counts.get(item.name, 0),
            }
            for item in items
        ],
    }
```

Apply to manage tables:

```python
@router.get("/manage/tables")
async def list_mysql_tables_manage(
    database: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    include_disabled: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mysql_config = await _load_mysql_config(db)
    if refresh:
        await _sync_tables(db, mysql_config, database)

    query = (
        select(MySQLTable)
        .where(MySQLTable.database_name == database)
        .order_by(MySQLTable.table_name.asc())
    )
    if not include_disabled:
        query = query.where(MySQLTable.enabled.is_(True))

    total, items = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "database": item.database_name,
                "name": item.table_name,
                "type": item.table_type,
                "comment": item.table_comment,
                "remark": item.remark,
                "enabled": item.enabled,
            }
            for item in items
        ],
    }
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_mysql_pagination.py -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add backend/app/api/mysql_metadata.py backend/tests/test_mysql_pagination.py
git commit -m "feat: paginate mysql list endpoints"
```

---

### Task 6: Frontend test setup for pagination (@test-driven-development)

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`

**Step 1: Write the failing test (usePagination, next task) first**

(Tests in Task 7 will fail until Vitest is installed/configured.)

**Step 2: Add test tooling**

Update `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "typescript": "^5.4.2",
    "vite": "^5.1.6",
    "vue-tsc": "^2.0.6",
    "vitest": "^1.6.0"
  }
}
```

Create `frontend/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  test: {
    environment: 'node'
  }
})
```

**Step 3: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL because tests in Task 7 import missing composable.

**Step 4: Commit**

```bash
git add frontend/package.json frontend/vitest.config.ts
git commit -m "chore: add vitest setup"
```

---

### Task 7: Frontend pagination composable (@test-driven-development)

**Files:**
- Create: `frontend/src/composables/usePagination.test.ts`
- Create: `frontend/src/composables/usePagination.ts`

**Step 1: Write the failing test**

Create `frontend/src/composables/usePagination.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { usePagination, DEFAULT_PAGE_SIZE } from './usePagination'


describe('usePagination', () => {
  it('defaults to page 1 and default page size', () => {
    const pagination = usePagination()

    expect(pagination.page.value).toBe(1)
    expect(pagination.pageSize.value).toBe(DEFAULT_PAGE_SIZE)
    expect(pagination.total.value).toBe(0)
  })

  it('clamps current page when total shrinks', () => {
    const pagination = usePagination(3, 10)
    pagination.setTotal(25)
    expect(pagination.maxPage.value).toBe(3)

    pagination.setTotal(15)
    expect(pagination.maxPage.value).toBe(2)
    expect(pagination.page.value).toBe(2)
  })

  it('resetPage sets page back to 1', () => {
    const pagination = usePagination(4, 20)
    pagination.resetPage()
    expect(pagination.page.value).toBe(1)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL with module not found for `usePagination`.

**Step 3: Write minimal implementation**

Create `frontend/src/composables/usePagination.ts`:

```ts
import { computed, ref } from 'vue'

export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

export function usePagination(initialPage = 1, initialPageSize = DEFAULT_PAGE_SIZE) {
  const page = ref(initialPage)
  const pageSize = ref(initialPageSize)
  const total = ref(0)

  const maxPage = computed(() => {
    return Math.max(1, Math.ceil(total.value / pageSize.value))
  })

  const setTotal = (value: number) => {
    total.value = value
    if (page.value > maxPage.value) {
      page.value = maxPage.value
    }
  }

  const resetPage = () => {
    page.value = 1
  }

  return {
    page,
    pageSize,
    total,
    maxPage,
    setTotal,
    resetPage
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/composables/usePagination.ts frontend/src/composables/usePagination.test.ts
git commit -m "feat: add pagination composable"
```

---

### Task 8: Frontend API pagination wiring tests (@test-driven-development)

**Files:**
- Create: `frontend/src/api/manage.test.ts`
- Modify: `frontend/src/api/manage.ts`

**Step 1: Write the failing test**

Create `frontend/src/api/manage.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getGitlabProjects,
  getGitlabUsers,
  getGitlabBranches,
  getGitlabCommits,
  getMysqlDatabasesManage,
  getMysqlTablesManage
} from './manage'

const getMock = vi.fn()
const patchMock = vi.fn()

vi.mock('@/utils/request', () => ({
  default: {
    get: getMock,
    patch: patchMock
  }
}))

beforeEach(() => {
  getMock.mockReset()
  patchMock.mockReset()
})

const mockPageResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20
}


describe('manage api pagination', () => {
  it('passes pagination params for gitlab projects', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabProjects(true, 2, 50)

    expect(getMock).toHaveBeenCalledWith('/gitlab/projects', {
      params: { include_disabled: true, page: 2, page_size: 50 }
    })
  })

  it('passes pagination params for gitlab users', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabUsers(true, 3, 20)

    expect(getMock).toHaveBeenCalledWith('/gitlab/users', {
      params: { include_disabled: true, page: 3, page_size: 20 }
    })
  })

  it('passes pagination params for gitlab branches', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabBranches(10, false, 2, 10)

    expect(getMock).toHaveBeenCalledWith('/gitlab/branches', {
      params: { project_id: 10, refresh: false, page: 2, page_size: 10 }
    })
  })

  it('passes pagination params for gitlab commits', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabCommits(10, 'main', false, 50, 1, 20)

    expect(getMock).toHaveBeenCalledWith('/gitlab/commits', {
      params: { project_id: 10, branch: 'main', refresh: false, limit: 50, page: 1, page_size: 20 }
    })
  })

  it('passes pagination params for mysql databases manage', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getMysqlDatabasesManage(false, true, 2, 10)

    expect(getMock).toHaveBeenCalledWith('/mysql/manage/databases', {
      params: { refresh: false, include_disabled: true, page: 2, page_size: 10 }
    })
  })

  it('passes pagination params for mysql tables manage', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getMysqlTablesManage('db_01', false, true, 3, 10)

    expect(getMock).toHaveBeenCalledWith('/mysql/manage/tables', {
      params: { database: 'db_01', refresh: false, include_disabled: true, page: 3, page_size: 10 }
    })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test`
Expected: FAIL because manage API functions do not accept pagination params or return page info.

**Step 3: Write minimal implementation**

Update `frontend/src/api/manage.ts`:

```ts
import request from '@/utils/request'

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ... existing interfaces

export async function getMysqlDatabasesManage(
  refresh = false,
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<MysqlDatabaseManage>>('/mysql/manage/databases', {
    params: { refresh, include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function getMysqlTablesManage(
  database: string,
  refresh = false,
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<MysqlTableManage>>('/mysql/manage/tables', {
    params: { database, refresh, include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function getGitlabProjects(
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabProjectManage>>('/gitlab/projects', {
    params: { include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function getGitlabUsers(
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabUserManage>>('/gitlab/users', {
    params: { include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function getGitlabBranches(
  projectId: number,
  refresh = false,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabBranch>>('/gitlab/branches', {
    params: { project_id: projectId, refresh, page, page_size: pageSize }
  })
}

export async function getGitlabCommits(
  projectId: number,
  branch: string,
  refresh = false,
  limit = 50,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabCommit>>('/gitlab/commits', {
    params: { project_id: projectId, branch, refresh, limit, page, page_size: pageSize }
  })
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/api/manage.ts frontend/src/api/manage.test.ts
git commit -m "feat: add pagination params to manage api"
```

---

### Task 9: Frontend list pagination wiring (manual verification)

**Files:**
- Modify: `frontend/src/components/settings/GitlabManage.vue`
- Modify: `frontend/src/components/settings/MysqlManage.vue`

**Step 1: Update GitlabManage.vue**

Add pagination state via `usePagination` for projects, users, branches, commits. Example additions:

```ts
import { usePagination, PAGE_SIZE_OPTIONS } from '@/composables/usePagination'

const projectPager = usePagination()
const userPager = usePagination()
const branchPager = usePagination()
const commitPager = usePagination()
```

Update loaders to pass page/page_size and set totals:

```ts
const loadProjects = async () => {
  projectsLoading.value = true
  try {
    const response = await getGitlabProjects(true, projectPager.page.value, projectPager.pageSize.value)
    projects.value = response.items || []
    projectPager.setTotal(response.total || 0)
  } finally {
    projectsLoading.value = false
  }
}
```

Repeat for users/branches/commits. Reset `branchPager`/`commitPager` when opening drawers:

```ts
const openBranches = async (row: GitlabProjectManage) => {
  currentProject.value = row
  branchPager.resetPage()
  branchesVisible.value = true
  await loadBranches(false)
}
```

Add `el-pagination` under each table/drawer:

```vue
<el-pagination
  v-model:current-page="projectPager.page"
  v-model:page-size="projectPager.pageSize"
  :page-sizes="PAGE_SIZE_OPTIONS"
  :total="projectPager.total"
  layout="total, sizes, prev, pager, next"
  @size-change="loadProjects"
  @current-change="loadProjects"
/>
```

**Step 2: Update MysqlManage.vue**

Add pagination state for databases/tables, update loaders to pass page/page_size and set totals, and add `el-pagination` under tables (and in drawer for tables).

**Step 3: Manual verification**

Run frontend and confirm:
- GitLab Projects/Users lists paginate and show correct totals
- Branches/Commits drawers paginate correctly
- MySQL Databases and Tables lists paginate correctly

Commands:

```bash
cd frontend
npm run dev
```

**Step 4: Commit**

```bash
git add frontend/src/components/settings/GitlabManage.vue frontend/src/components/settings/MysqlManage.vue
git commit -m "feat: paginate gitlab/mysql management lists"
```

---

### Task 10: End-to-end verification (@verification-before-completion)

**Files:**
- None (verification only)

**Step 1: Backend tests**

Run:

```bash
cd backend
pytest tests/test_pagination_utils.py -v
pytest tests/test_gitlab_pagination.py -v
pytest tests/test_mysql_pagination.py -v
```

Expected: all PASS.

**Step 2: Frontend tests**

Run:

```bash
cd frontend
npm test
```

Expected: PASS.

**Step 3: Manual UI check**

Use the UI to validate pagination flows as listed in Task 9.

**Step 4: Final commit (if needed)**

```bash
git status --short
```

Ensure only intended files are modified.

---

## Notes
- This plan assumes we stay in the current workspace (no worktree skill available).
- Use @test-driven-development for all code changes, and @verification-before-completion before declaring success.
