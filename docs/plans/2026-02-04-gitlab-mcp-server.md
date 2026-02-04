# GitLab MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a GitLab MCP server that lists projects, users, recent commits, and commit diffs using `.env` configuration.

**Architecture:** A `fastmcp` server module in `backend/mcp-server/gitlab-mcp-server/server.py` loads config with `python-dotenv`, connects to GitLab via `python-gitlab`, and exposes four read-only tools. Helpers provide group parsing, limit clamping, pagination, and diff truncation.

**Tech Stack:** Python 3.14, fastmcp, python-gitlab, python-dotenv, pytest.

---

### Task 1: Add helper tests and minimal helpers

**Files:**
- Create: `backend/mcp-server/gitlab-mcp-server/tests/test_helpers.py`
- Create: `backend/mcp-server/gitlab-mcp-server/server.py`

**Step 1: Write the failing test**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import server


def test_parse_groups_empty():
    assert server._parse_groups(None) == []
    assert server._parse_groups("") == []


def test_parse_groups_splits_and_strips():
    assert server._parse_groups("group-a, group-b ,group-c") == [
        "group-a",
        "group-b",
        "group-c",
    ]


def test_clamp_limit_defaults_and_caps():
    assert server._clamp_limit(None) == 20
    assert server._clamp_limit(0) == 20
    assert server._clamp_limit(-5) == 20
    assert server._clamp_limit(5) == 5
    assert server._clamp_limit(999) == 200


def test_truncate_patch():
    assert server._truncate_patch("short", 10) == "short"
    assert server._truncate_patch("abcdef", 3) == "abc... [truncated]"
    assert server._truncate_patch(None, 10) == ""
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_helpers.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing attributes.

**Step 3: Write minimal implementation**

```python
import logging
import os
import sys
from typing import List, Optional
from dotenv import load_dotenv
import gitlab
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

load_dotenv()

mcp = FastMCP("GitLab MCP Server")

DEFAULT_LIMIT = 20
MAX_LIMIT = 200


def _parse_groups(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _clamp_limit(limit: Optional[int]) -> int:
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def _truncate_patch(patch: Optional[str], max_chars: int) -> str:
    if not patch or max_chars <= 0:
        return ""
    if len(patch) <= max_chars:
        return patch
    return patch[:max_chars] + "... [truncated]"
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_helpers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/mcp-server/gitlab-mcp-server/server.py \
  backend/mcp-server/gitlab-mcp-server/tests/test_helpers.py
git commit -m "test: add helper tests for gitlab mcp"
```

### Task 2: Add tool tests for list_projects and list_users

**Files:**
- Create: `backend/mcp-server/gitlab-mcp-server/tests/test_tools.py`
- Modify: `backend/mcp-server/gitlab-mcp-server/server.py`

**Step 1: Write the failing test**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import server


class StubProjects:
    def __init__(self, items):
        self._items = items

    def list(self, **_kwargs):
        return self._items


class StubGroup:
    def __init__(self, name, projects):
        self.name = name
        self.projects = StubProjects(projects)


class StubGroups:
    def __init__(self, groups):
        self._groups = groups

    def list(self, **_kwargs):
        return self._groups


class StubUsers:
    def __init__(self, users):
        self._users = users

    def list(self, **_kwargs):
        return self._users


class StubGL:
    def __init__(self, groups, users):
        self.groups = StubGroups(groups)
        self.users = StubUsers(users)


class StubProject:
    def __init__(self, project_id, name_with_namespace, web_url, last_activity_at):
        self.id = project_id
        self.name_with_namespace = name_with_namespace
        self.path_with_namespace = name_with_namespace
        self.web_url = web_url
        self.last_activity_at = last_activity_at


class StubUser:
    def __init__(self, user_id, name, username, state):
        self.id = user_id
        self.name = name
        self.username = username
        self.state = state


def test_list_projects_uses_groups(monkeypatch):
    groups = [
        StubGroup(
            "group-a",
            [
                StubProject(1, "group-a/proj-1", "https://gitlab/proj-1", "2024-01-01"),
            ],
        ),
        StubGroup(
            "group-b",
            [
                StubProject(2, "group-b/proj-2", "https://gitlab/proj-2", "2024-01-02"),
            ],
        ),
    ]
    gl = StubGL(groups, users=[])

    def _stub_connect():
        return gl

    monkeypatch.setenv("GITLAB_GROUPS", "group-b")
    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.list_projects()
    assert result == [
        {
            "id": 2,
            "name_with_namespace": "group-b/proj-2",
            "path_with_namespace": "group-b/proj-2",
            "web_url": "https://gitlab/proj-2",
            "last_activity_at": "2024-01-02",
        }
    ]


def test_list_users(monkeypatch):
    users = [
        StubUser(10, "Alice", "alice", "active"),
        StubUser(11, "Bob", "bob", "blocked"),
    ]
    gl = StubGL(groups=[], users=users)

    def _stub_connect():
        return gl

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.list_users()
    assert result == [
        {"id": 10, "name": "Alice", "username": "alice", "state": "active"},
        {"id": 11, "name": "Bob", "username": "bob", "state": "blocked"},
    ]
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: FAIL (missing `_connect_gitlab` or tool functions).

**Step 3: Write minimal implementation**

```python
import logging
import os
import sys
from typing import List, Optional
from dotenv import load_dotenv
import gitlab
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

load_dotenv()

mcp = FastMCP("GitLab MCP Server")

DEFAULT_LIMIT = 20
MAX_LIMIT = 200
DEFAULT_PER_PAGE = 50

_gl = None


def _parse_groups(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _clamp_limit(limit: Optional[int]) -> int:
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def _truncate_patch(patch: Optional[str], max_chars: int) -> str:
    if not patch or max_chars <= 0:
        return ""
    if len(patch) <= max_chars:
        return patch
    return patch[:max_chars] + "... [truncated]"


def _connect_gitlab(gitlab_module=gitlab):
    global _gl
    if _gl is not None:
        return _gl

    url = os.getenv("GITLAB_URL")
    token = os.getenv("GITLAB_TOKEN")
    api_version = os.getenv("GITLAB_API_VERSION", "4")
    if not url or not token:
        raise Exception("Missing GITLAB_URL or GITLAB_TOKEN")

    _gl = gitlab_module.Gitlab(url=url, private_token=token, api_version=api_version)
    _gl.auth()
    return _gl


def _list_all(listable, per_page: int):
    page = 1
    items = []
    while True:
        page_items = listable.list(page=page, per_page=per_page)
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < per_page:
            break
        page += 1
    return items


@mcp.tool()
def list_projects():
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    groups = _parse_groups(os.getenv("GITLAB_GROUPS"))
    gl = _connect_gitlab()

    projects = []
    if groups:
        all_groups = _list_all(gl.groups, per_page)
        for group in all_groups:
            if group.name in groups:
                projects.extend(_list_all(group.projects, per_page))
    else:
        projects = _list_all(gl.projects, per_page)

    return [
        {
            "id": project.id,
            "name_with_namespace": project.name_with_namespace,
            "path_with_namespace": project.path_with_namespace,
            "web_url": project.web_url,
            "last_activity_at": project.last_activity_at,
        }
        for project in projects
    ]


@mcp.tool()
def list_users():
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()
    users = _list_all(gl.users, per_page)
    return [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "state": user.state,
        }
        for user in users
    ]
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/mcp-server/gitlab-mcp-server/server.py \
  backend/mcp-server/gitlab-mcp-server/tests/test_tools.py
git commit -m "feat: add gitlab list tools"
```

### Task 3: Add tool tests for list_commits and get_commit_diff

**Files:**
- Modify: `backend/mcp-server/gitlab-mcp-server/tests/test_tools.py`
- Modify: `backend/mcp-server/gitlab-mcp-server/server.py`

**Step 1: Write the failing test**

```python
class StubCommit:
    def __init__(self, commit_id, short_id, title, author_name, created_at, web_url):
        self.id = commit_id
        self.short_id = short_id
        self.title = title
        self.author_name = author_name
        self.created_at = created_at
        self.web_url = web_url

    def diff(self):
        return [
            {
                "old_path": "a.txt",
                "new_path": "a.txt",
                "diff": "x" * 10,
            }
        ]


class StubCommits:
    def __init__(self, commits):
        self._commits = commits

    def list(self, **_kwargs):
        return self._commits

    def get(self, _sha):
        return self._commits[0]


class StubProjectWithCommits:
    def __init__(self, commits):
        self.commits = StubCommits(commits)


class StubProjectsAPI:
    def __init__(self, project):
        self._project = project

    def get(self, _project_id):
        return self._project


def test_list_commits(monkeypatch):
    commits = [
        StubCommit("abc", "abc", "Fix", "Alice", "2024-01-01", "https://gitlab/c/1"),
        StubCommit("def", "def", "Add", "Bob", "2024-01-02", "https://gitlab/c/2"),
    ]
    project = StubProjectWithCommits(commits)

    class StubGL2:
        def __init__(self, project):
            self.projects = StubProjectsAPI(project)

    def _stub_connect():
        return StubGL2(project)

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.list_commits(123, limit=1)
    assert result == [
        {
            "id": "abc",
            "short_id": "abc",
            "title": "Fix",
            "author_name": "Alice",
            "created_at": "2024-01-01",
            "web_url": "https://gitlab/c/1",
        }
    ]


def test_get_commit_diff_truncates(monkeypatch):
    commits = [
        StubCommit("abc", "abc", "Fix", "Alice", "2024-01-01", "https://gitlab/c/1"),
    ]
    project = StubProjectWithCommits(commits)

    class StubGL2:
        def __init__(self, project):
            self.projects = StubProjectsAPI(project)

    def _stub_connect():
        return StubGL2(project)

    monkeypatch.setenv("GITLAB_MAX_DIFF_CHARS", "5")
    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.get_commit_diff(123, "abc")
    assert result["id"] == "abc"
    assert result["diffs"][0]["diff"] == "xxxxx... [truncated]"
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: FAIL (missing list_commits / get_commit_diff or truncation).

**Step 3: Write minimal implementation**

```python
@mcp.tool()
def list_commits(project_id: int, limit: int = DEFAULT_LIMIT):
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()

    commits = []
    remaining = _clamp_limit(limit)
    page = 1
    while remaining > 0:
        page_items = gl.projects.get(project_id).commits.list(
            page=page, per_page=min(per_page, remaining)
        )
        if not page_items:
            break
        commits.extend(page_items)
        remaining -= len(page_items)
        if len(page_items) < min(per_page, remaining + len(page_items)):
            break
        page += 1

    return [
        {
            "id": commit.id,
            "short_id": commit.short_id,
            "title": commit.title,
            "author_name": commit.author_name,
            "created_at": commit.created_at,
            "web_url": commit.web_url,
        }
        for commit in commits
    ]


@mcp.tool()
def get_commit_diff(project_id: int, commit_sha: str):
    if not commit_sha:
        raise Exception("commit_sha is required")

    max_diff_chars = int(os.getenv("GITLAB_MAX_DIFF_CHARS", "200000"))
    gl = _connect_gitlab()
    project = gl.projects.get(project_id)
    commit = project.commits.get(commit_sha)

    diffs = []
    for item in commit.diff():
        diffs.append(
            {
                "old_path": item.get("old_path"),
                "new_path": item.get("new_path"),
                "diff": _truncate_patch(item.get("diff"), max_diff_chars),
            }
        )

    return {
        "id": commit.id,
        "short_id": commit.short_id,
        "title": commit.title,
        "author_name": commit.author_name,
        "created_at": commit.created_at,
        "web_url": commit.web_url,
        "diffs": diffs,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/mcp-server/gitlab-mcp-server/tests/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/mcp-server/gitlab-mcp-server/server.py \
  backend/mcp-server/gitlab-mcp-server/tests/test_tools.py
git commit -m "feat: add gitlab commit tools"
```

### Task 4: Add README, .env.example, and connection test

**Files:**
- Create: `backend/mcp-server/gitlab-mcp-server/README.md`
- Create: `backend/mcp-server/gitlab-mcp-server/.env.example`
- Create: `backend/mcp-server/gitlab-mcp-server/test_connection.py`

**Step 1: Add documentation and example config**

```env
# GitLab MCP Server configuration
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_token_here
GITLAB_GROUPS=group-a,group-b
GITLAB_API_VERSION=4
GITLAB_PER_PAGE=50
GITLAB_MAX_DIFF_CHARS=200000
```

```markdown
# GitLab MCP Server

A read-only MCP server for GitLab that lists projects, users, commits, and commit diffs.

## Features
- list_projects
- list_users
- list_commits
- get_commit_diff

## Setup

```bash
pip install python-gitlab fastmcp python-dotenv
```

Create `.env` from `.env.example` and fill in credentials.

## Run

```bash
python server.py
```

## Claude Desktop example

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "python",
      "args": ["/path/to/gitlab-mcp-server/server.py"],
      "env": {
        "GITLAB_URL": "https://gitlab.example.com",
        "GITLAB_TOKEN": "your_token_here",
        "GITLAB_GROUPS": "group-a,group-b"
      }
    }
  }
}
```
```

```python
#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import gitlab

    print("=" * 50)
    print("GitLab MCP Server connection test")
    print("=" * 50)

    url = os.getenv("GITLAB_URL")
    token = os.getenv("GITLAB_TOKEN")
    if not url or not token:
        raise Exception("Missing GITLAB_URL or GITLAB_TOKEN")

    gl = gitlab.Gitlab(url=url, private_token=token, api_version=os.getenv("GITLAB_API_VERSION", "4"))
    gl.auth()

    user = gl.user
    print("Connected as:", user.username)
    print("OK")
except Exception as exc:
    print("Connection failed:", exc)
    sys.exit(1)
```

**Step 2: Commit**

```bash
git add backend/mcp-server/gitlab-mcp-server/README.md \
  backend/mcp-server/gitlab-mcp-server/.env.example \
  backend/mcp-server/gitlab-mcp-server/test_connection.py
git commit -m "docs: add gitlab mcp server usage"
```
