import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import DeclarativeBase

from app.utils.pagination import paginate_query


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))


@pytest.mark.asyncio
async def test_paginate_query_returns_total_and_page_items():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        session.add_all([Item(name=f"item-{idx:02d}") for idx in range(1, 51)])
        await session.commit()

    async with Session() as session:
        query = select(Item).order_by(Item.id.asc())
        total, items = await paginate_query(session, query, page=2, page_size=10)

        assert total == 50
        assert len(items) == 10
        assert [item.name for item in items] == [f"item-{idx:02d}" for idx in range(11, 21)]

    await engine.dispose()


@pytest.mark.asyncio
async def test_paginate_query_out_of_range_returns_empty_items():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        session.add_all([Item(name=f"item-{idx:02d}") for idx in range(1, 21)])
        await session.commit()

    async with Session() as session:
        query = select(Item).order_by(Item.id.asc())
        total, items = await paginate_query(session, query, page=3, page_size=10)

        assert total == 20
        assert items == []

    await engine.dispose()
