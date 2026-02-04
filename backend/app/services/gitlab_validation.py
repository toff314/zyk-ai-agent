"""GitLab token validation helper."""
import gitlab


def validate_gitlab_token(url: str, token: str, gitlab_module=gitlab) -> dict:
    if not url or not token:
        raise ValueError("url and token are required")

    gl = gitlab_module.Gitlab(url=url, private_token=token, api_version="4")
    gl.auth()
    user = gl.user
    return {
        "id": getattr(user, "id", None),
        "username": getattr(user, "username", None),
        "name": getattr(user, "name", None),
    }


def validate_gitlab_groups(groups: str) -> str:
    if not groups:
        raise ValueError("groups is required")
    items = [item.strip() for item in groups.split(",") if item.strip()]
    if not items:
        raise ValueError("groups is required")
    return ",".join(items)
