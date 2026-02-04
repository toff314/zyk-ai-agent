from app.agents.prompts import CODE_REVIEW_PROMPT


def render_code_review_prompt(diff: str, notice: str | None = None) -> str:
    content = diff or "(未提供diff内容)"
    diff_notice = notice or ""
    prompt = CODE_REVIEW_PROMPT.replace("{{DIFF}}", content)
    prompt = prompt.replace("{{DIFF_NOTICE}}", diff_notice)
    return prompt
