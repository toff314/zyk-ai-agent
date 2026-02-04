"""
GitLab 用户同步服务（基于 MCP GitLab 工具）
"""
import logging
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import safe_commit
from app.models.gitlab_user import GitLabUser
from app.models.gitlab_project import GitLabProject
from app.models.gitlab_branch import GitLabBranch
from app.models.gitlab_commit import GitLabCommit
from app.models.gitlab_commit_diff import GitLabCommitDiff
from app.services.mcp_gitlab import MCPGitLabClient

logger = logging.getLogger(__name__)


async def sync_gitlab_users(
    db: AsyncSession,
    gitlab_config: dict,
    client: MCPGitLabClient | None = None,
) -> dict:
    """同步GitLab用户到本地缓存表"""
    client = client or MCPGitLabClient()
    users = await client.list_users(gitlab_config)

    existing = (await db.execute(select(GitLabUser))).scalars().all()
    existing_map = {item.id: item for item in existing}

    await db.execute(delete(GitLabUser))
    for user in users:
        prev = existing_map.get(user.get("id"))
        db.add(
            GitLabUser(
                id=user.get("id"),
                username=user.get("username") or "",
                name=user.get("name"),
                avatar_url=user.get("avatar_url"),
                remark=prev.remark if prev else None,
                enabled=prev.enabled if prev else True,
                commits_week=0,
                commits_month=0,
            )
        )

    await safe_commit(db)
    logger.info("同步GitLab用户完成: %s", len(users))
    return {"success": True, "user_count": len(users)}


async def sync_gitlab_projects(
    db: AsyncSession,
    gitlab_config: dict,
    client: MCPGitLabClient | None = None,
) -> dict:
    """同步GitLab项目到本地缓存表"""
    client = client or MCPGitLabClient()
    projects = await client.list_projects(gitlab_config)

    existing = (await db.execute(select(GitLabProject))).scalars().all()
    existing_map = {item.id: item for item in existing}

    await db.execute(delete(GitLabProject))
    for project in projects:
        prev = existing_map.get(project.get("id"))
        db.add(
            GitLabProject(
                id=project.get("id"),
                name=project.get("name_with_namespace") or project.get("name"),
                path_with_namespace=project.get("path_with_namespace") or "",
                web_url=project.get("web_url"),
                last_activity_at=project.get("last_activity_at"),
                remark=prev.remark if prev else None,
                enabled=prev.enabled if prev else True,
            )
        )

    await safe_commit(db)
    logger.info("同步GitLab项目完成: %s", len(projects))
    return {"success": True, "project_count": len(projects)}


async def sync_gitlab_branches(
    db: AsyncSession,
    gitlab_config: dict,
    project_id: int,
    client: MCPGitLabClient | None = None,
) -> dict:
    client = client or MCPGitLabClient()
    branches = await client.list_branches(gitlab_config, project_id)

    await db.execute(delete(GitLabBranch).where(GitLabBranch.project_id == project_id))
    for branch in branches:
        db.add(
            GitLabBranch(
                project_id=project_id,
                name=branch.get("name") or "",
                commit_sha=branch.get("commit_sha"),
                committed_date=branch.get("committed_date"),
            )
        )
    await safe_commit(db)
    return {"success": True, "branch_count": len(branches)}


async def sync_gitlab_commits(
    db: AsyncSession,
    gitlab_config: dict,
    project_id: int,
    branch: str,
    limit: int = 50,
    client: MCPGitLabClient | None = None,
) -> dict:
    client = client or MCPGitLabClient()
    commits = await client.list_commits(gitlab_config, project_id, limit=limit, ref_name=branch)

    await db.execute(
        delete(GitLabCommit).where(
            GitLabCommit.project_id == project_id,
            GitLabCommit.branch == branch,
        )
    )
    for commit in commits:
        db.add(
            GitLabCommit(
                project_id=project_id,
                branch=branch,
                commit_sha=commit.get("id"),
                title=commit.get("title"),
                author_name=commit.get("author_name"),
                created_at=commit.get("created_at"),
                web_url=commit.get("web_url"),
            )
        )
    await safe_commit(db)
    return {"success": True, "commit_count": len(commits)}


async def sync_gitlab_commit_diffs(
    db: AsyncSession,
    gitlab_config: dict,
    project_id: int,
    commit_sha: str,
    client: MCPGitLabClient | None = None,
) -> dict:
    client = client or MCPGitLabClient()
    commit = await client.get_commit_diff(gitlab_config, project_id, commit_sha)
    diffs = commit.get("diffs") or []

    await db.execute(
        delete(GitLabCommitDiff).where(
            GitLabCommitDiff.project_id == project_id,
            GitLabCommitDiff.commit_sha == commit_sha,
        )
    )
    for diff in diffs:
        db.add(
            GitLabCommitDiff(
                project_id=project_id,
                commit_sha=commit_sha,
                old_path=diff.get("old_path"),
                new_path=diff.get("new_path"),
                diff=diff.get("diff"),
            )
        )
    await safe_commit(db)
    return {"success": True, "diff_count": len(diffs)}


async def sync_all_gitlab_branches(db: AsyncSession, gitlab_config: dict) -> dict:
    projects = (await db.execute(select(GitLabProject))).scalars().all()
    total = 0
    for project in projects:
        result = await sync_gitlab_branches(db, gitlab_config, project.id)
        total += result.get("branch_count", 0)
    return {"success": True, "branch_count": total}
