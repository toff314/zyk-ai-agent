import pytest
from app.api import chat


def test_get_chat_templates_by_mode_normal():
    items = chat.get_chat_templates_by_mode("normal")
    assert isinstance(items, list)
    assert items


def test_get_chat_templates_by_mode_invalid():
    with pytest.raises(ValueError):
        chat.get_chat_templates_by_mode("unknown")
