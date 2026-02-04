import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import server


def test_connect_gitlab_uses_timeout(monkeypatch):
    captured = {}

    class StubGitlab:
        def __init__(self, url, private_token, api_version, timeout):
            captured["url"] = url
            captured["token"] = private_token
            captured["api_version"] = api_version
            captured["timeout"] = timeout

        def auth(self):
            return None

    class StubModule:
        Gitlab = StubGitlab

    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com")
    monkeypatch.setenv("GITLAB_TOKEN", "token-1")
    monkeypatch.setenv("GITLAB_API_VERSION", "4")
    monkeypatch.setenv("GITLAB_TIMEOUT", "120")
    monkeypatch.setattr(server, "_gl", None)

    server._connect_gitlab(gitlab_module=StubModule)

    assert captured["timeout"] == 120.0

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


class StubCommit:
    def __init__(self, commit_id, short_id, title, author_name, created_at, web_url):
        self.id = commit_id
        self.short_id = short_id
        self.title = title
        self.author_name = author_name
        self.created_at = created_at
        self.web_url = web_url
        self.author_email = None

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


class StubBranch:
    def __init__(self, name, sha, date):
        self.name = name
        self.commit = {"id": sha, "committed_date": date}


class StubBranches:
    def __init__(self, branches):
        self._branches = branches

    def list(self, **_kwargs):
        return self._branches


class StubProjectWithCommits:
    def __init__(self, commits, project_id=1, name="proj-1"):
        self.id = project_id
        self.name = name
        self.commits = StubCommits(commits)
        self.branches = StubBranches([])


class StubProjectsAPI:
    def __init__(self, project):
        self._project = project

    def get(self, _project_id):
        return self._project


class StubProjectsMapAPI:
    def __init__(self, mapping):
        self._mapping = mapping

    def get(self, project_id):
        return self._mapping[project_id]


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

    result = server.list_projects.fn()
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
    users[0].avatar_url = "https://gitlab/avatar"
    users[1].avatar_url = None
    gl = StubGL(groups=[], users=users)

    def _stub_connect():
        return gl

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.list_users.fn()
    assert result == [
        {
            "id": 10,
            "name": "Alice",
            "username": "alice",
            "state": "active",
            "avatar_url": "https://gitlab/avatar",
        },
        {
            "id": 11,
            "name": "Bob",
            "username": "bob",
            "state": "blocked",
            "avatar_url": None,
        },
    ]


def test_get_user_commits(monkeypatch):
    commits = [
        StubCommit("abc", "abc", "Fix", "Alice", "2024-01-01", "https://gitlab/c/1"),
        StubCommit("def", "def", "Add", "Bob", "2024-01-02", "https://gitlab/c/2"),
    ]
    project = StubProjectWithCommits(commits, project_id=99, name="proj-x")

    user = StubUser(10, "Alice", "alice", "active")
    user.email = "alice@example.com"

    class StubUsersWithFilter:
        def list(self, **kwargs):
            if kwargs.get("username") == "alice":
                return [user]
            return []

    class StubGL2:
        def __init__(self):
            self.users = StubUsersWithFilter()
            self.projects = StubProjectsMapAPI({99: project})

    def _stub_connect():
        return StubGL2()

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.get_user_commits.fn("alice", project_ids=[99], limit=5)
    assert result == [
        {
            "id": "abc",
            "title": "Fix",
            "message": None,
            "author_name": "Alice",
            "authored_date": "2024-01-01",
            "project_id": 99,
            "project_name": "proj-x",
            "web_url": "https://gitlab/c/1",
        }
    ]


def test_get_user_commits_logs(monkeypatch, caplog):
    commits = [
        StubCommit("abc", "abc", "Fix", "Alice", "2024-01-01", "https://gitlab/c/1"),
    ]
    project = StubProjectWithCommits(commits, project_id=1, name="proj-1")

    user = StubUser(10, "Alice", "alice", "active")

    class StubUsersWithFilter:
        def list(self, **kwargs):
            if kwargs.get("username") == "alice":
                return [user]
            return []

    class StubGL2:
        def __init__(self):
            self.users = StubUsersWithFilter()
            self.projects = StubProjectsMapAPI({1: project})

    def _stub_connect():
        return StubGL2()

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)
    caplog.set_level(logging.WARNING, logger="gitlab-mcp-server")

    server.get_user_commits.fn("alice", project_ids=[1], limit=1)

    assert "get_user_commits" in caplog.text


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

    result = server.list_commits.fn(123, limit=1)
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

    result = server.get_commit_diff.fn(123, "abc")
    assert result["id"] == "abc"
    assert result["diffs"][0]["diff"] == "xxxxx... [truncated]"


def test_list_branches(monkeypatch):
    branches = [
        StubBranch("main", "abc", "2024-01-01"),
        StubBranch("dev", "def", "2024-01-02"),
    ]

    class ProjectWithBranches(StubProjectWithCommits):
        def __init__(self):
            super().__init__([])
            self.branches = StubBranches(branches)

    project = ProjectWithBranches()

    class StubGL2:
        def __init__(self, project):
            self.projects = StubProjectsAPI(project)

    def _stub_connect():
        return StubGL2(project)

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.list_branches.fn(123)
    assert result == [
        {"name": "dev", "commit_sha": "def", "committed_date": "2024-01-02"},
        {"name": "main", "commit_sha": "abc", "committed_date": "2024-01-01"},
    ]
