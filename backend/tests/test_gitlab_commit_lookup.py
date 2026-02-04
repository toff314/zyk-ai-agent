import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.gitlab_commit import GitLabCommit
from app.utils.gitlab_commit_lookup import resolve_commit_project_id


def test_resolve_commit_project_id_from_db():
    async def run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            session.add(
                GitLabCommit(
                    project_id=42,
                    branch="main",
                    commit_sha="abc123",
                    title="Test commit",
                )
            )
            await session.commit()
            project_id = await resolve_commit_project_id(session, "abc123")

        await engine.dispose()
        return project_id

    assert asyncio.run(run()) == 42
