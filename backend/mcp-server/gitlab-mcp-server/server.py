import logging
import os
import sys
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import gitlab
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("gitlab-mcp-server")

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
    timeout = float(os.getenv("GITLAB_TIMEOUT", "120"))
    if not url or not token:
        raise Exception("Missing GITLAB_URL or GITLAB_TOKEN")

    _gl = gitlab_module.Gitlab(
        url=url,
        private_token=token,
        api_version=api_version,
        timeout=timeout,
    )
    _gl.auth()
    return _gl


def _list_all(listable, per_page: int, **kwargs):
    page = 1
    items = []
    while True:
        page_items = listable.list(page=page, per_page=per_page, **kwargs)
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < per_page:
            break
        page += 1
    return items


def _get_attr(item, name, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _get_now() -> datetime:
    override = os.getenv("GITLAB_NOW")
    if override:
        parsed = _parse_iso_datetime(override)
        if parsed:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
    return datetime.now(timezone.utc)


def _count_user_commit_stats(user, per_page: int, start_week: datetime, start_month: datetime) -> tuple[int, int]:
    events_api = _get_attr(user, "events")
    if not events_api:
        return 0, 0

    try:
        events = _list_all(events_api, per_page, after=start_month.date().isoformat())
    except Exception as exc:
        logger.warning("Failed to load events for user %s: %s", _get_attr(user, "username"), exc)
        return 0, 0

    commits_week = 0
    commits_month = 0
    for event in events:
        push_data = _get_attr(event, "push_data")
        if not push_data:
            continue
        commit_count = _get_attr(push_data, "commit_count", 0)
        try:
            commit_count = int(commit_count)
        except (TypeError, ValueError):
            commit_count = 0
        if commit_count <= 0:
            continue

        commits_month += commit_count

        created_at = _get_attr(event, "created_at")
        created_dt = _parse_iso_datetime(created_at)
        if created_dt and created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        if created_dt and created_dt >= start_week:
            commits_week += commit_count

    return commits_week, commits_month


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

    items = [
        {
            "id": project.id,
            "name_with_namespace": project.name_with_namespace,
            "path_with_namespace": project.path_with_namespace,
            "web_url": project.web_url,
            "last_activity_at": project.last_activity_at,
        }
        for project in projects
    ]
    items.sort(key=lambda item: item.get("last_activity_at") or "", reverse=True)
    return items


@mcp.tool()
def list_users():
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()
    users = _list_all(gl.users, per_page)
    now = _get_now()
    start_week = (now - timedelta(days=now.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    users.sort(
        key=lambda user: (
            getattr(user, "last_activity_on", None)
            or getattr(user, "created_at", None)
            or ""
        ),
        reverse=True,
    )
    items = []
    for user in users:
        commits_week, commits_month = _count_user_commit_stats(
            user,
            per_page,
            start_week,
            start_month,
        )
        items.append(
            {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "state": user.state,
                "avatar_url": getattr(user, "avatar_url", None),
                "commits_week": commits_week,
                "commits_month": commits_month,
            }
        )
    return items


@mcp.tool()
def get_user_commits(username: str, project_ids: List[int], limit: int = DEFAULT_LIMIT):
    if not username:
        raise Exception("username is required")
    if not project_ids:
        raise Exception("project_ids is required")

    logger.warning(
        "get_user_commits username=%s limit=%s projects=%s",
        username,
        limit,
        len(project_ids),
    )

    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()

    users = gl.users.list(username=username)
    if not users:
        return []

    user = users[0]
    commits = []
    remaining = _clamp_limit(limit)
    for project_id in project_ids:
        if remaining <= 0:
            break
        try:
            project = gl.projects.get(project_id)
        except Exception:
            continue
        try:
            project_commits = project.commits.list(page=1, per_page=min(per_page, remaining))
        except Exception:
            continue

        for commit in project_commits:
            author_name = getattr(commit, "author_name", None)
            author_email = getattr(commit, "author_email", None)
            user_name = getattr(user, "name", None)
            user_email = getattr(user, "email", None)
            if author_name != user_name and author_email != user_email:
                continue
            authored_date = getattr(commit, "authored_date", None) or getattr(commit, "created_at", None)
            commits.append(
                {
                    "id": commit.id,
                    "title": commit.title,
                    "message": getattr(commit, "message", None),
                    "author_name": author_name,
                    "authored_date": authored_date,
                    "project_id": project_id,
                    "project_name": getattr(project, "name", None),
                    "web_url": getattr(commit, "web_url", None),
                }
            )

        remaining = _clamp_limit(limit) - len(commits)

    commits.sort(key=lambda item: item.get("authored_date") or "", reverse=True)
    return commits[: _clamp_limit(limit)]


@mcp.tool()
def list_commits(project_id: int, limit: int = DEFAULT_LIMIT, ref_name: Optional[str] = None):
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()

    commits = []
    remaining = _clamp_limit(limit)
    page = 1
    while remaining > 0:
        page_size = min(per_page, remaining)
        list_kwargs = {"page": page, "per_page": page_size}
        if ref_name:
            list_kwargs["ref_name"] = ref_name
        page_items = gl.projects.get(project_id).commits.list(**list_kwargs)
        if not page_items:
            break
        if len(page_items) > remaining:
            page_items = page_items[:remaining]
            commits.extend(page_items)
            break
        commits.extend(page_items)
        remaining -= len(page_items)
        if len(page_items) < page_size:
            break
        page += 1

    items = [
        {
            "id": commit.id,
            "short_id": commit.short_id,
            "title": commit.title,
            "author_name": commit.author_name,
            "created_at": commit.created_at,
            "web_url": commit.web_url,
        }
        for commit in commits
    ]
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return items


@mcp.tool()
def list_branches(project_id: int):
    per_page = int(os.getenv("GITLAB_PER_PAGE", DEFAULT_PER_PAGE))
    gl = _connect_gitlab()
    project = gl.projects.get(project_id)
    branches = _list_all(project.branches, per_page)
    items = [
        {
            "name": branch.name,
            "commit_sha": branch.commit.get("id") if hasattr(branch, "commit") else None,
            "committed_date": branch.commit.get("committed_date") if hasattr(branch, "commit") else None,
        }
        for branch in branches
    ]
    items.sort(key=lambda item: item.get("committed_date") or "", reverse=True)
    return items


@mcp.tool()
def get_commit_diff(project_id: int, commit_sha: str):
    if not commit_sha:
        raise Exception("commit_sha is required")

    max_diff_chars = int(os.getenv("GITLAB_MAX_DIFF_CHARS", "200000"))
    gl = _connect_gitlab()
    project = gl.projects.get(project_id)
    commit = project.commits.get(commit_sha)

    diffs = []
    for item in commit.diff():
        diffs.append(
            {
                "old_path": item.get("old_path"),
                "new_path": item.get("new_path"),
                "diff": _truncate_patch(item.get("diff"), max_diff_chars),
            }
        )

    return {
        "id": commit.id,
        "short_id": commit.short_id,
        "title": commit.title,
        "author_name": commit.author_name,
        "created_at": commit.created_at,
        "web_url": commit.web_url,
        "diffs": diffs,
    }


if __name__ == "__main__":
    mcp.run()
