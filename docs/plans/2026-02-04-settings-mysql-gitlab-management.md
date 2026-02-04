# Settings MySQL & GitLab Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add MySQL/GitLab management tabs in Settings with enable/disable + remark (alias) support, cached GitLab project/branch/commit/diff views, and @ mention mapping that respects enable/remark.

**Architecture:** Extend existing cache tables (MySQLDatabase/MySQLTable/GitLabUser/GitLabProject) with `enabled` and `remark`, add GitLab branch/commit/diff cache tables, and implement sync services that preserve metadata. Create management API endpoints to list/update/refresh data. Update chat mention parsing to map alias → original names while filtering disabled entries, and expand @ token parsing to include Chinese. Frontend Settings adds new tabs with nested list/detail views that call the new APIs.

**Tech Stack:** FastAPI, SQLAlchemy Async, python-gitlab, fastmcp, Vue 3, Element Plus, pytest.

---

### Task 1: Models for enable/remark + GitLab cache tables

**Files:**
- Modify: `backend/app/models/mysql_database.py`
- Modify: `backend/app/models/mysql_table.py`
- Modify: `backend/app/models/gitlab_user.py`
- Modify: `backend/app/models/gitlab_project.py`
- Create: `backend/app/models/gitlab_branch.py`
- Create: `backend/app/models/gitlab_commit.py`
- Create: `backend/app/models/gitlab_commit_diff.py`
- Modify: `backend/app/models/database.py`
- Test: `backend/tests/test_model_defaults.py`

**Step 1: Write the failing test**

```python
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.models.gitlab_user import GitLabUser
from app.models.gitlab_project import GitLabProject


def test_default_enabled_and_remark():
    assert MySQLDatabase().enabled is True
    assert MySQLDatabase().remark is None
    assert MySQLTable().enabled is True
    assert MySQLTable().remark is None
    assert GitLabUser().enabled is True
    assert GitLabUser().remark is None
    assert GitLabProject().enabled is True
    assert GitLabProject().remark is None
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_model_defaults.py -v`
Expected: FAIL (missing fields).

**Step 3: Write minimal implementation**

```python
# mysql_database.py
from sqlalchemy import Column, Boolean
remark = Column(String(255), nullable=True)
enabled = Column(Boolean, default=True, nullable=False)

# mysql_table.py
from sqlalchemy import Column, Boolean
remark = Column(String(255), nullable=True)
enabled = Column(Boolean, default=True, nullable=False)

# gitlab_user.py, gitlab_project.py
from sqlalchemy import Column, Boolean
remark = Column(String(255), nullable=True)
enabled = Column(Boolean, default=True, nullable=False)

# gitlab_branch.py
class GitLabBranch(Base):
  __tablename__ = "gitlab_branches"
  id = Column(Integer, primary_key=True, autoincrement=True)
  project_id = Column(Integer, index=True)
  name = Column(String(200), index=True)
  commit_sha = Column(String(64))
  committed_date = Column(String(50))
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  __table_args__ = (Index("idx_gitlab_branch_project_name", "project_id", "name", unique=True),)

# gitlab_commit.py
class GitLabCommit(Base):
  __tablename__ = "gitlab_commits"
  id = Column(Integer, primary_key=True, autoincrement=True)
  project_id = Column(Integer, index=True)
  branch = Column(String(200), index=True)
  commit_sha = Column(String(64), index=True)
  title = Column(String(500))
  author_name = Column(String(200))
  created_at = Column(String(50))
  web_url = Column(String(500))
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  __table_args__ = (Index("idx_gitlab_commit_project_branch_sha", "project_id", "branch", "commit_sha", unique=True),)

# gitlab_commit_diff.py
class GitLabCommitDiff(Base):
  __tablename__ = "gitlab_commit_diffs"
  id = Column(Integer, primary_key=True, autoincrement=True)
  project_id = Column(Integer, index=True)
  commit_sha = Column(String(64), index=True)
  old_path = Column(String(500))
  new_path = Column(String(500))
  diff = Column(String)
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  __table_args__ = (Index("idx_gitlab_diff_project_commit_path", "project_id", "commit_sha", "new_path", unique=True),)
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_model_defaults.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/*.py backend/tests/test_model_defaults.py

git commit -m "feat: add enable/remark fields and gitlab cache models"
```

---

### Task 2: GitLab MCP tools for branches/commits

**Files:**
- Modify: `backend/mcp-server/gitlab-mcp-server/server.py`
- Modify: `backend/mcp-server/gitlab-mcp-server/tests/test_tools.py`
- Modify: `backend/app/services/mcp_gitlab.py`

**Step 1: Write the failing test**

```python
# in test_tools.py
class StubBranch:
    def __init__(self, name, sha, date):
        self.name = name
        self.commit = {"id": sha, "committed_date": date}

# add test_list_branches
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: FAIL (missing list_branches, ref_name support).

**Step 3: Write minimal implementation**

```python
@mcp.tool()
def list_branches(project_id: int):
    gl = _connect_gitlab()
    project = gl.projects.get(project_id)
    branches = _list_all(project.branches, per_page)
    return [{"name": b.name, "commit_sha": b.commit.get("id"), "committed_date": b.commit.get("committed_date")} for b in branches]

@mcp.tool()
def list_commits(project_id: int, limit: int = DEFAULT_LIMIT, ref_name: str | None = None):
    ... commits.list(ref_name=ref_name)
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/mcp-server/gitlab-mcp-server/server.py backend/mcp-server/gitlab-mcp-server/tests/test_tools.py backend/app/services/mcp_gitlab.py

git commit -m "feat: add gitlab branch/commit mcp tools"
```

---

### Task 3: Sync services for GitLab branches/commits/diffs and preserve remarks

**Files:**
- Modify: `backend/app/services/gitlab_sync.py`
- Modify: `backend/app/services/mysql_sync.py`
- Test: `backend/tests/test_config_sync.py`

**Step 1: Write the failing test**

```python
# extend test_config_sync.py
async def test_sync_preserves_remark_enabled():
    session = StubSession()
    # seed existing MySQLDatabase with remark/enabled false
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_config_sync.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# mysql_sync.py
# upsert: keep existing remark/enabled; delete items not in remote

# gitlab_sync.py
async def sync_gitlab_branches(db, config, project_id, client=None): ...
async def sync_gitlab_commits(db, config, project_id, branch, limit=50, client=None): ...
async def sync_gitlab_commit_diffs(db, config, project_id, commit_sha, client=None): ...
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_config_sync.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/gitlab_sync.py backend/app/services/mysql_sync.py backend/tests/test_config_sync.py

git commit -m "feat: add gitlab cache sync and preserve remarks"
```

---

### Task 4: MySQL management APIs + @ mapping

**Files:**
- Modify: `backend/app/api/mysql_metadata.py`
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/mcp_mysql.py`
- Test: `backend/tests/test_mysql_mentions.py`

**Step 1: Write the failing test**

```python
# test_mysql_mentions.py
from app.api.chat import _resolve_db_table_mentions
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_mysql_mentions.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add endpoints:
  - `GET /api/v1/mysql/databases?include_disabled=&with_counts=`
  - `GET /api/v1/mysql/tables?database=&include_disabled=`
  - `PATCH /api/v1/mysql/databases/{db_id}`
  - `PATCH /api/v1/mysql/tables/{table_id}`
  - `GET /api/v1/mysql/table-detail?database=&table=`
- Extend `mcp_mysql` with `describe_table` wrapper.
- Update `chat.py`:
  - Expand `AT_TOKEN_PATTERN` to include Chinese
  - Add async mapping `_resolve_db_table_mentions(db, message)` that maps alias → original name using enabled records only.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_mysql_mentions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/mysql_metadata.py backend/app/api/chat.py backend/app/services/mcp_mysql.py backend/tests/test_mysql_mentions.py

git commit -m "feat: mysql management api + mention mapping"
```

---

### Task 5: GitLab management APIs + cached views

**Files:**
- Create: `backend/app/api/gitlab_manage.py`
- Modify: `backend/app/__init__.py`
- Modify: `backend/app/api/chat.py`
- Test: `backend/tests/test_gitlab_manage.py`

**Step 1: Write the failing test**

```python
# test_gitlab_manage.py
# test list projects/users respects enabled + remark
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_gitlab_manage.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Endpoints:
- `GET /api/v1/gitlab/projects?include_disabled=&with_counts=`
- `PATCH /api/v1/gitlab/projects/{project_id}`
- `GET /api/v1/gitlab/users?include_disabled=`
- `PATCH /api/v1/gitlab/users/{user_id}`
- `GET /api/v1/gitlab/branches?project_id=&refresh=`
- `GET /api/v1/gitlab/commits?project_id=&branch=&refresh=`
- `GET /api/v1/gitlab/commit-diffs?project_id=&commit=&refresh=`

Also update `chat.py` code-review path to map @alias → username (filter disabled).

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_gitlab_manage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/gitlab_manage.py backend/app/__init__.py backend/app/api/chat.py backend/tests/test_gitlab_manage.py

git commit -m "feat: gitlab management apis + mention mapping"
```

---

### Task 6: Frontend API + Settings UI tabs

**Files:**
- Create: `frontend/src/api/manage.ts`
- Modify: `frontend/src/views/Settings.vue`
- Create: `frontend/src/components/settings/MysqlManage.vue`
- Create: `frontend/src/components/settings/GitlabManage.vue`

**Step 1: Write the failing test**

N/A (no FE tests). Use manual verification.

**Step 2: Write minimal implementation**

- Add Settings tabs: “Mysql管理” and “Gitlab管理”.
- MySQL management: database list with table_count, enabled switch, remark input, and “查看表” drawer. Table list with enable/remark and “详情” drawer (columns from API).
- GitLab management: project list with branch_count, enabled switch, remark, “查看分支”. Branch list with “查看提交”; commit list with “查看diff”.

**Step 3: Manual verify**

- Ensure @ mention dropdown uses remark display and disabled items are hidden.
- Verify saving remark updates backend and is reflected in mention list.

**Step 4: Commit**

```bash
git add frontend/src/api/manage.ts frontend/src/views/Settings.vue frontend/src/components/settings/*.vue

git commit -m "feat: add mysql/gitlab management tabs"
```

---

### Task 7: End-to-end verification

**Step 1: Run backend tests**

Run:
- `pytest backend/tests/test_config_sync.py -v`
- `pytest backend/tests/test_gitlab_validation.py -v`
- `pytest backend/tests/test_mysql_mentions.py -v`

**Step 2: Manual UI checks**

- Settings → Mysql管理: enable/remark updates, table detail.
- Settings → Gitlab管理: project→branch→commit→diff views.
- Chat @ mention behavior for disabled items.

**Step 3: Commit (if needed)**

```bash
git add -A

git commit -m "chore: verify mysql/gitlab management"
```
