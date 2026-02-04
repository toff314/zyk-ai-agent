from app.utils.gitlab_username import normalize_gitlab_username


def test_normalize_gitlab_username_strips_leading_at():
    assert normalize_gitlab_username("@yuanwu") == "yuanwu"


def test_normalize_gitlab_username_trims_whitespace():
    assert normalize_gitlab_username("  yuanwu  ") == "yuanwu"
