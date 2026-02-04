import pytest

from app.services.gitlab_validation import validate_gitlab_token, validate_gitlab_groups


class StubUser:
    def __init__(self):
        self.id = 7
        self.username = "alice"
        self.name = "Alice"


class StubGitlab:
    def __init__(self, url, private_token, api_version):
        self.url = url
        self.private_token = private_token
        self.api_version = api_version
        self._user = StubUser()
        self.auth_called = False

    def auth(self):
        self.auth_called = True

    @property
    def user(self):
        return self._user


class StubModule:
    Gitlab = StubGitlab


def test_validate_gitlab_token_returns_user():
    result = validate_gitlab_token("https://gitlab.example.com", "token", gitlab_module=StubModule)
    assert result["username"] == "alice"
    assert result["name"] == "Alice"
    assert result["id"] == 7


def test_validate_gitlab_token_requires_url_and_token():
    with pytest.raises(ValueError):
        validate_gitlab_token("", "token", gitlab_module=StubModule)
    with pytest.raises(ValueError):
        validate_gitlab_token("https://gitlab.example.com", "", gitlab_module=StubModule)


def test_validate_gitlab_groups_normalizes():
    assert validate_gitlab_groups("seccloud, team ,foo") == "seccloud,team,foo"


def test_validate_gitlab_groups_requires_non_empty():
    with pytest.raises(ValueError):
        validate_gitlab_groups("")
    with pytest.raises(ValueError):
        validate_gitlab_groups(" , ")
