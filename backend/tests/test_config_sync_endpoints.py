import json
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.config import Config
from app.api.config import sync_gitlab_data, sync_mysql_data


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


async def seed_gitlab_config(session):
    session.add(
        Config(
            key="gitlab_config",
            value=json.dumps({"url": "http://gitlab", "token": "t", "groups": "g"}),
        )
    )
    await session.commit()


async def seed_mysql_config(session):
    session.add(
        Config(
            key="mysql_config",
            value=json.dumps({
                "enabled": True,
                "host": "localhost",
                "port": 3306,
                "user": "u",
                "password": "p",
                "database": "db",
                "timeout": 60,
            }),
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_sync_gitlab_data_uses_saved_config(monkeypatch, async_session):
    await seed_gitlab_config(async_session)

    async def fake_sync_users(db, config, client=None):
        return {"success": True, "user_count": 1}

    async def fake_sync_projects(db, config, client=None):
        return {"success": True, "project_count": 2}

    async def fake_sync_branches(db, config):
        return {"success": True, "branch_count": 3}

    monkeypatch.setattr("app.api.config.sync_gitlab_users", fake_sync_users)
    monkeypatch.setattr("app.api.config.sync_gitlab_projects", fake_sync_projects)
    monkeypatch.setattr("app.api.config.sync_all_gitlab_branches", fake_sync_branches)

    result = await sync_gitlab_data(db=async_session, current_user=type("U", (), {"role": "admin"})())

    assert result["code"] == 0
    assert "同步成功" in result["sync"]["message"]


@pytest.mark.asyncio
async def test_sync_mysql_data_uses_saved_config(monkeypatch, async_session):
    await seed_mysql_config(async_session)

    async def fake_sync_mysql(db, config):
        return {"database_count": 1, "table_count": 2}

    monkeypatch.setattr("app.api.config.sync_mysql_metadata", fake_sync_mysql)

    result = await sync_mysql_data(db=async_session, current_user=type("U", (), {"role": "admin"})())

    assert result["code"] == 0
    assert "同步成功" in result["sync"]["message"]
