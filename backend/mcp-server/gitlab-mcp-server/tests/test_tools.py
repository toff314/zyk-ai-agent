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
    gl = StubGL(groups=[], users=users)

    def _stub_connect():
        return gl

    monkeypatch.setattr(server, "_connect_gitlab", _stub_connect)

    result = server.list_users.fn()
    assert result == [
        {"id": 10, "name": "Alice", "username": "alice", "state": "active"},
        {"id": 11, "name": "Bob", "username": "bob", "state": "blocked"},
    ]


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
