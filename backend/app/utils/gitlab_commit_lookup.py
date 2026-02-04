from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gitlab_commit import GitLabCommit


async def resolve_commit_project_id(db: AsyncSession, commit_sha: str) -> int | None:
    result = await db.execute(
        select(GitLabCommit.project_id)
        .where(GitLabCommit.commit_sha == commit_sha)
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None
