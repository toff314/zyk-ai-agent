import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.gitlab_user import GitLabUser
from app.models.gitlab_project import GitLabProject
from app.models.gitlab_branch import GitLabBranch
from app.models.gitlab_commit import GitLabCommit
from app.api.gitlab_manage import (
    list_gitlab_users,
    list_gitlab_projects,
    list_gitlab_branches,
    list_gitlab_commits,
)


@pytest.fixture
async def async_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


async def seed_gitlab_users(session, count=25):
    session.add_all(
        [
            GitLabUser(username=f"user-{idx:02d}", name=f"User {idx:02d}")
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


async def seed_gitlab_projects(session, count=15):
    session.add_all(
        [
            GitLabProject(
                name=f"project-{idx:02d}",
                path_with_namespace=f"group/project-{idx:02d}",
            )
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


async def seed_gitlab_branches(session, project_id=1, count=25):
    session.add_all(
        [
            GitLabBranch(
                project_id=project_id,
                name=f"branch-{idx:02d}",
                commit_sha=f"sha-{idx:02d}",
            )
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


async def seed_gitlab_commits(session, project_id=1, branch="main", count=25):
    session.add_all(
        [
            GitLabCommit(
                project_id=project_id,
                branch=branch,
                commit_sha=f"commit-{idx:02d}",
                title=f"Commit {idx:02d}",
                author_name="Tester",
                created_at=f"2026-02-04T00:{idx:02d}:00Z",
            )
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_list_gitlab_users_paginates(async_session):
    await seed_gitlab_users(async_session, 25)

    result = await list_gitlab_users(
        include_disabled=True,
        page=2,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert [item["username"] for item in result["items"]] == [
        f"user-{idx:02d}" for idx in range(11, 21)
    ]


@pytest.mark.asyncio
async def test_list_gitlab_projects_paginates(async_session):
    await seed_gitlab_projects(async_session, 15)

    result = await list_gitlab_projects(
        include_disabled=True,
        page=2,
        page_size=5,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 15
    assert result["page"] == 2
    assert result["page_size"] == 5
    assert [item["path_with_namespace"] for item in result["items"]] == [
        f"group/project-{idx:02d}" for idx in range(6, 11)
    ]


@pytest.mark.asyncio
async def test_list_gitlab_users_filters_by_name(async_session):
    await seed_gitlab_users(async_session, 10)

    result = await list_gitlab_users(
        include_disabled=True,
        page=1,
        page_size=10,
        name="User 03",
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 1
    assert [item["username"] for item in result["items"]] == ["user-03"]


@pytest.mark.asyncio
async def test_list_gitlab_projects_filters_by_name(async_session):
    await seed_gitlab_projects(async_session, 10)

    result = await list_gitlab_projects(
        include_disabled=True,
        page=1,
        page_size=10,
        name="group/project-04",
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 1
    assert [item["path_with_namespace"] for item in result["items"]] == ["group/project-04"]


@pytest.mark.asyncio
async def test_list_gitlab_branches_paginates(async_session):
    await seed_gitlab_branches(async_session, project_id=1, count=25)

    result = await list_gitlab_branches(
        project_id=1,
        refresh=False,
        page=3,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 3
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"branch-{idx:02d}" for idx in range(21, 26)
    ]


@pytest.mark.asyncio
async def test_list_gitlab_commits_paginates(async_session):
    await seed_gitlab_commits(async_session, project_id=1, branch="main", count=25)

    result = await list_gitlab_commits(
        project_id=1,
        branch="main",
        refresh=False,
        limit=50,
        page=1,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 1
    assert result["page_size"] == 10
    # created_at desc: latest is 25
    assert result["items"][0]["commit_sha"] == "commit-25"
