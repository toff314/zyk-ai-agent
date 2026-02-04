from app.agents import prompts


def test_data_analysis_prompt_includes_table_context_instructions():
    assert "DB_TABLE_CONTEXT" in prompts.DATA_ANALYSIS_PROMPT
    assert "execute_mysql_query" in prompts.DATA_ANALYSIS_PROMPT
    assert "list_databases" in prompts.DATA_ANALYSIS_PROMPT
    assert "describe_table" in prompts.DATA_ANALYSIS_PROMPT


def test_code_review_prompt_includes_gitlab_tools():
    assert "get_user_commits" in prompts.CODE_REVIEW_PROMPT
    assert "get_commit_diff" in prompts.CODE_REVIEW_PROMPT


def test_chat_templates_exist():
    assert isinstance(prompts.CHAT_TEMPLATES, list)
    assert isinstance(prompts.DATA_ANALYSIS_TEMPLATES, list)
    assert isinstance(prompts.CODE_REVIEW_TEMPLATES, list)
    assert "data_analysis" in prompts.TEMPLATES_BY_MODE
