"""GitLab management API."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.database import get_db, safe_commit
from app.models.config import Config
from app.models.gitlab_project import GitLabProject
from app.models.gitlab_user import GitLabUser
from app.models.gitlab_branch import GitLabBranch
from app.models.gitlab_commit import GitLabCommit
from app.models.gitlab_commit_diff import GitLabCommitDiff
from app.middleware.auth import get_current_user
from app.services.gitlab_sync import (
    sync_gitlab_branches,
    sync_gitlab_commits,
    sync_gitlab_commit_diffs,
)
from app.utils.validation import normalize_remark
from app.utils.pagination import paginate_query, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gitlab", tags=["GitLab管理"])


def _load_gitlab_config_value(db_config: Config) -> dict:
    try:
        config = json.loads(db_config.value)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitLab配置解析失败")
    if not config.get("url") or not config.get("token"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先配置GitLab连接信息")
    return config


async def _load_gitlab_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Config).where(Config.key == "gitlab_config"))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先配置GitLab连接信息")
    return _load_gitlab_config_value(config)


@router.get("/projects")
async def list_gitlab_projects(
    include_disabled: bool = Query(True),
    name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(GitLabProject).order_by(GitLabProject.path_with_namespace.asc())
    if not include_disabled:
        query = query.where(GitLabProject.enabled.is_(True))
    if name:
        trimmed = name.strip()
        if trimmed:
            pattern = f"%{trimmed}%"
            query = query.where(
                or_(
                    GitLabProject.name.ilike(pattern),
                    GitLabProject.path_with_namespace.ilike(pattern),
                )
            )

    total, items = await paginate_query(db, query, page, page_size)

    count_result = await db.execute(
        select(GitLabBranch.project_id, func.count())
        .group_by(GitLabBranch.project_id)
    )
    branch_counts = {row[0]: row[1] for row in count_result.all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "path_with_namespace": item.path_with_namespace,
                "web_url": item.web_url,
                "last_activity_at": item.last_activity_at,
                "remark": item.remark,
                "enabled": item.enabled,
                "branch_count": branch_counts.get(item.id, 0),
            }
            for item in items
        ],
    }


@router.patch("/projects/{project_id}")
async def update_gitlab_project(
    project_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(GitLabProject).where(GitLabProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    if "enabled" in payload:
        project.enabled = bool(payload.get("enabled"))
    if "remark" in payload:
        try:
            project.remark = normalize_remark(payload.get("remark"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await safe_commit(db)
    return {"success": True}


@router.get("/users")
async def list_gitlab_users(
    include_disabled: bool = Query(True),
    name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(GitLabUser).order_by(GitLabUser.username.asc())
    if not include_disabled:
        query = query.where(GitLabUser.enabled.is_(True))
    if name:
        trimmed = name.strip()
        if trimmed:
            pattern = f"%{trimmed}%"
            query = query.where(
                or_(
                    GitLabUser.username.ilike(pattern),
                    GitLabUser.name.ilike(pattern),
                )
            )

    total, users = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "remark": user.remark,
                "enabled": user.enabled,
                "commits_week": user.commits_week,
                "commits_month": user.commits_month,
            }
            for user in users
        ],
    }


@router.patch("/users/{user_id}")
async def update_gitlab_user(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(GitLabUser).where(GitLabUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if "enabled" in payload:
        user.enabled = bool(payload.get("enabled"))
    if "remark" in payload:
        try:
            user.remark = normalize_remark(payload.get("remark"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await safe_commit(db)
    return {"success": True}


@router.get("/branches")
async def list_gitlab_branches(
    project_id: int = Query(...),
    refresh: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gitlab_config = await _load_gitlab_config(db)
    if refresh:
        await sync_gitlab_branches(db, gitlab_config, project_id)

    query = (
        select(GitLabBranch)
        .where(GitLabBranch.project_id == project_id)
        .order_by(GitLabBranch.name.asc())
    )
    total, branches = await paginate_query(db, query, page, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "name": branch.name,
                "commit_sha": branch.commit_sha,
                "committed_date": branch.committed_date,
            }
            for branch in branches
        ],
    }


@router.get("/commits")
async def list_gitlab_commits(
    project_id: int = Query(...),
    branch: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gitlab_config = await _load_gitlab_config(db)
    if refresh:
        await sync_gitlab_commits(db, gitlab_config, project_id, branch, limit=limit)

    query = (
        select(GitLabCommit)
        .where(
            GitLabCommit.project_id == project_id,
            GitLabCommit.branch == branch,
        )
        .order_by(GitLabCommit.created_at.desc())
    )
    total, commits = await paginate_query(db, query, page, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "commit_sha": item.commit_sha,
                "title": item.title,
                "author_name": item.author_name,
                "created_at": item.created_at,
                "web_url": item.web_url,
            }
            for item in commits
        ],
    }


@router.get("/commit-diffs")
async def list_gitlab_commit_diffs(
    project_id: int = Query(...),
    commit: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gitlab_config = await _load_gitlab_config(db)
    if refresh:
        await sync_gitlab_commit_diffs(db, gitlab_config, project_id, commit)

    result = await db.execute(
        select(GitLabCommitDiff)
        .where(
            GitLabCommitDiff.project_id == project_id,
            GitLabCommitDiff.commit_sha == commit,
        )
        .order_by(GitLabCommitDiff.new_path.asc())
    )
    diffs = result.scalars().all()
    return {
        "total": len(diffs),
        "items": [
            {
                "old_path": diff.old_path,
                "new_path": diff.new_path,
                "diff": diff.diff,
            }
            for diff in diffs
        ],
    }
