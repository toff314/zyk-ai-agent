"""Validation helpers."""
import re
from typing import Optional


REMARK_PATTERN = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff]+$")


def normalize_remark(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("备注仅支持中文、字母、数字、下划线")
    trimmed = value.strip()
    if not trimmed:
        return None
    if not REMARK_PATTERN.fullmatch(trimmed):
        raise ValueError("备注仅支持中文、字母、数字、下划线")
    return trimmed
