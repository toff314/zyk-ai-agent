from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


def get_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


async def paginate_query(
    db: AsyncSession,
    query: Select,
    page: int,
    page_size: int,
):
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one() or 0

    offset = get_offset(page, page_size)
    items_result = await db.execute(query.offset(offset).limit(page_size))
    items = items_result.scalars().all()
    return total, items
