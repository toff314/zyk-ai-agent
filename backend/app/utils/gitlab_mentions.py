import re


AT_TOKEN_PATTERN = re.compile(r'@([\u4e00-\u9fffA-Za-z0-9_]+)')


def normalize_gitlab_mentions(message: str, alias_map: dict[str, str]) -> str:
    def _replace(match: re.Match) -> str:
        token = match.group(1)
        actual = alias_map.get(token)
        if not actual:
            return ""
        return actual

    cleaned = AT_TOKEN_PATTERN.sub(_replace, message)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
