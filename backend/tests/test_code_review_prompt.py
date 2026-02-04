from app.utils.code_review_prompt import render_code_review_prompt


def test_render_code_review_prompt_includes_diff_and_notice():
    diff = "diff --git a/a.py b/a.py\n+print('hi')"
    notice = "diff过长，已截断"

    prompt = render_code_review_prompt(diff, notice)

    assert diff in prompt
    assert notice in prompt
