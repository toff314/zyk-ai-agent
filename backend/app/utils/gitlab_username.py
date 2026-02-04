def normalize_gitlab_username(value: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("@"):
        trimmed = trimmed[1:]
    return trimmed.strip()
