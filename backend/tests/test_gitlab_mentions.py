from app.utils.gitlab_mentions import normalize_gitlab_mentions


def test_normalize_gitlab_mentions_replaces_with_username():
    message = "@袁兀 查看他的最近提交情况"
    alias_map = {"袁兀": "yuanwu"}

    result = normalize_gitlab_mentions(message, alias_map)

    assert result == "yuanwu 查看他的最近提交情况"
