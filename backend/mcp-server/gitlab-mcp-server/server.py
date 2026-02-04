import logging
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
import gitlab
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

load_dotenv()

mcp = FastMCP("GitLab MCP Server")

DEFAULT_LIMIT = 20
MAX_LIMIT = 200
DEFAULT_PER_PAGE = 50
_gl = None


def _parse_groups(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _clamp_limit(limit: Optional[int]) -> int:
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def _truncate_patch(patch: Optional[str], max_chars: int) -> str:
    if not patch or max_chars <= 0:
        return ""
    if len(patch) <= max_chars:
        return patch
    return patch[:max_chars] + "... [truncated]"


def _connect_gitlab(gitlab_module=gitlab):
    global _gl
    if _gl is not None:
        return _gl

    url = os.getenv("GITLAB_URL")
    token = os.getenv("GITLAB_TOKEN")
    api_version = os.getenv("GITLAB_API_VERSION", "4")
    if not url or not token:
        raise Exception("Missing GITLAB_URL or GITLAB_TOKEN")

    _gl = gitlab_module.Gitlab(url=url, private_token=token, api_version=api_version)
    _gl.auth()
    return _gl


def _list_all(listable, per_page: int):
    page = 1
    items = []
    while True:
        page_items = listable.list(page=page, per_page=per_page)
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < per_page:
            break
        page += 1
    return items


@mcp.tool()
def list_projects():
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    groups = _parse_groups(os.getenv("GITLAB_GROUPS"))
    gl = _connect_gitlab()

    projects = []
    if groups:
        all_groups = _list_all(gl.groups, per_page)
        for group in all_groups:
            if group.name in groups:
                projects.extend(_list_all(group.projects, per_page))
    else:
        projects = _list_all(gl.projects, per_page)

    return [
        {
            "id": project.id,
            "name_with_namespace": project.name_with_namespace,
            "path_with_namespace": project.path_with_namespace,
            "web_url": project.web_url,
            "last_activity_at": project.last_activity_at,
        }
        for project in projects
    ]


@mcp.tool()
def list_users():
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()
    users = _list_all(gl.users, per_page)
    return [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "state": user.state,
        }
        for user in users
    ]


if __name__ == "__main__":
    mcp.run()
