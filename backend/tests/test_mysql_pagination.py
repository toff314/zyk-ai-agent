import json
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.config import Config
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.api.mysql_metadata import (
    list_mysql_databases,
    list_mysql_tables,
    list_mysql_databases_manage,
    list_mysql_tables_manage,
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


async def seed_mysql_config(session):
    config = Config(
        key="mysql_config",
        value=json.dumps(
            {
                "enabled": True,
                "host": "",
                "port": 3306,
                "user": "",
                "password": "",
                "database": "",
                "timeout": 60,
            }
        ),
    )
    session.add(config)
    await session.commit()


async def seed_mysql_databases(session, count=25):
    session.add_all(
        [MySQLDatabase(name=f"db_{idx:02d}") for idx in range(1, count + 1)]
    )
    await session.commit()


async def seed_mysql_tables(session, database="db_01", count=25):
    session.add_all(
        [
            MySQLTable(database_name=database, table_name=f"table_{idx:02d}")
            for idx in range(1, count + 1)
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_list_mysql_databases_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_databases(async_session, 25)

    result = await list_mysql_databases(
        refresh=False,
        include_disabled=True,
        page=2,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"db_{idx:02d}" for idx in range(11, 21)
    ]


@pytest.mark.asyncio
async def test_list_mysql_databases_filters_by_name(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_databases(async_session, 12)

    result = await list_mysql_databases(
        refresh=False,
        include_disabled=True,
        page=1,
        page_size=10,
        name="db_03",
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 1
    assert [item["name"] for item in result["items"]] == ["db_03"]


@pytest.mark.asyncio
async def test_list_mysql_tables_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_tables(async_session, database="db_01", count=25)

    result = await list_mysql_tables(
        database="db_01",
        refresh=False,
        include_disabled=True,
        page=3,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 3
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"table_{idx:02d}" for idx in range(21, 26)
    ]


@pytest.mark.asyncio
async def test_list_mysql_tables_filters_by_name(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_tables(async_session, database="db_01", count=12)

    result = await list_mysql_tables(
        database="db_01",
        refresh=False,
        include_disabled=True,
        page=1,
        page_size=10,
        name="table_02",
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 1
    assert [item["name"] for item in result["items"]] == ["table_02"]


@pytest.mark.asyncio
async def test_list_mysql_databases_manage_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_databases(async_session, 25)
    await seed_mysql_tables(async_session, database="db_01", count=3)

    result = await list_mysql_databases_manage(
        refresh=False,
        include_disabled=True,
        page=1,
        page_size=5,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 25
    assert result["page"] == 1
    assert result["page_size"] == 5
    assert len(result["items"]) == 5


@pytest.mark.asyncio
async def test_list_mysql_databases_manage_filters_by_name(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_databases(async_session, 10)

    result = await list_mysql_databases_manage(
        refresh=False,
        include_disabled=True,
        page=1,
        page_size=10,
        name="db_04",
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 1
    assert [item["name"] for item in result["items"]] == ["db_04"]


@pytest.mark.asyncio
async def test_list_mysql_tables_manage_paginates(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_tables(async_session, database="db_02", count=21)

    result = await list_mysql_tables_manage(
        database="db_02",
        refresh=False,
        include_disabled=True,
        page=2,
        page_size=10,
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 21
    assert result["page"] == 2
    assert result["page_size"] == 10
    assert [item["name"] for item in result["items"]] == [
        f"table_{idx:02d}" for idx in range(11, 21)
    ]


@pytest.mark.asyncio
async def test_list_mysql_tables_manage_filters_by_name(async_session):
    await seed_mysql_config(async_session)
    await seed_mysql_tables(async_session, database="db_02", count=12)

    result = await list_mysql_tables_manage(
        database="db_02",
        refresh=False,
        include_disabled=True,
        page=1,
        page_size=10,
        name="table_01",
        db=async_session,
        current_user=None,
    )

    assert result["total"] == 1
    assert [item["name"] for item in result["items"]] == ["table_01"]
