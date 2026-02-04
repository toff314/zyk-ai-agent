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
