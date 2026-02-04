"""
MySQL 元数据API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.database import get_db, safe_commit
from app.models.config import Config
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.middleware.auth import get_current_user
from app.services.mysql_sync import sync_mysql_databases, sync_mysql_tables
from app.utils.validation import normalize_remark
from app.utils.pagination import paginate_query, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
import json
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/mysql", tags=["MySQL元数据"])


async def _load_mysql_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Config).where(Config.key == "mysql_config"))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先配置MySQL连接信息")
    try:
        mysql_config = json.loads(config.value)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MySQL配置解析失败")
    if not mysql_config.get("enabled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MySQL未启用")
    return mysql_config


async def _sync_databases(db: AsyncSession, mysql_config: dict) -> list[dict]:
    """同步MySQL数据库列表"""
    databases = await sync_mysql_databases(db, mysql_config)
    logger.info("同步MySQL数据库完成: %s", len(databases))
    return databases


async def _sync_tables(db: AsyncSession, mysql_config: dict, database: str) -> list[dict]:
    """同步指定数据库的表列表"""
    tables = await sync_mysql_tables(db, mysql_config, database)
    logger.info("同步MySQL表完成: %s (%s)", database, len(tables))
    return tables


@router.get("/databases")
async def list_mysql_databases(
    refresh: bool = Query(False),
    include_disabled: bool = Query(False),
    name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    获取数据库列表（可选刷新）
    """
    mysql_config = await _load_mysql_config(db)

    if refresh:
        await _sync_databases(db, mysql_config)

    query = select(MySQLDatabase).order_by(MySQLDatabase.name.asc())
    if not include_disabled:
        query = query.where(MySQLDatabase.enabled.is_(True))
    if name:
        trimmed = name.strip()
        if trimmed:
            query = query.where(MySQLDatabase.name.ilike(f"%{trimmed}%"))

    total, items = await paginate_query(db, query, page, page_size)

    if not items and total == 0 and not name:
        await _sync_databases(db, mysql_config)
        total, items = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "remark": item.remark,
                "enabled": item.enabled,
            }
            for item in items
        ],
    }


@router.get("/tables")
async def list_mysql_tables(
    database: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    include_disabled: bool = Query(False),
    name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    获取指定数据库的表列表（可选刷新）
    """
    mysql_config = await _load_mysql_config(db)

    if refresh:
        await _sync_tables(db, mysql_config, database)

    query = (
        select(MySQLTable)
        .where(MySQLTable.database_name == database)
        .order_by(MySQLTable.table_name.asc())
    )
    if not include_disabled:
        query = query.where(MySQLTable.enabled.is_(True))
    if name:
        trimmed = name.strip()
        if trimmed:
            query = query.where(MySQLTable.table_name.ilike(f"%{trimmed}%"))

    total, items = await paginate_query(db, query, page, page_size)

    if not items and total == 0 and not name:
        await _sync_tables(db, mysql_config, database)
        total, items = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "database": item.database_name,
                "name": item.table_name,
                "type": item.table_type,
                "comment": item.table_comment,
                "remark": item.remark,
                "enabled": item.enabled,
            }
            for item in items
        ]
    }


@router.get("/manage/databases")
async def list_mysql_databases_manage(
    refresh: bool = Query(False),
    include_disabled: bool = Query(True),
    name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mysql_config = await _load_mysql_config(db)
    if refresh:
        await _sync_databases(db, mysql_config)

    query = select(MySQLDatabase).order_by(MySQLDatabase.name.asc())
    if not include_disabled:
        query = query.where(MySQLDatabase.enabled.is_(True))
    if name:
        trimmed = name.strip()
        if trimmed:
            query = query.where(MySQLDatabase.name.ilike(f"%{trimmed}%"))

    total, items = await paginate_query(db, query, page, page_size)

    count_result = await db.execute(
        select(MySQLTable.database_name, func.count())
        .group_by(MySQLTable.database_name)
    )
    counts = {row[0]: row[1] for row in count_result.all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "remark": item.remark,
                "enabled": item.enabled,
                "table_count": counts.get(item.name, 0),
            }
            for item in items
        ],
    }


@router.get("/manage/tables")
async def list_mysql_tables_manage(
    database: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    include_disabled: bool = Query(True),
    name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mysql_config = await _load_mysql_config(db)
    if refresh:
        await _sync_tables(db, mysql_config, database)

    query = (
        select(MySQLTable)
        .where(MySQLTable.database_name == database)
        .order_by(MySQLTable.table_name.asc())
    )
    if not include_disabled:
        query = query.where(MySQLTable.enabled.is_(True))
    if name:
        trimmed = name.strip()
        if trimmed:
            query = query.where(MySQLTable.table_name.ilike(f"%{trimmed}%"))

    total, items = await paginate_query(db, query, page, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "database": item.database_name,
                "name": item.table_name,
                "type": item.table_type,
                "comment": item.table_comment,
                "remark": item.remark,
                "enabled": item.enabled,
            }
            for item in items
        ],
    }


@router.patch("/manage/databases/{database_id}")
async def update_mysql_database_manage(
    database_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(MySQLDatabase).where(MySQLDatabase.id == database_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据库不存在")

    if "enabled" in payload:
        item.enabled = bool(payload.get("enabled"))
    if "remark" in payload:
        try:
            item.remark = normalize_remark(payload.get("remark"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await safe_commit(db)
    return {"success": True}


@router.patch("/manage/tables/{table_id}")
async def update_mysql_table_manage(
    table_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(MySQLTable).where(MySQLTable.id == table_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据表不存在")

    if "enabled" in payload:
        item.enabled = bool(payload.get("enabled"))
    if "remark" in payload:
        try:
            item.remark = normalize_remark(payload.get("remark"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    await safe_commit(db)
    return {"success": True}


@router.get("/manage/table-detail")
async def get_mysql_table_detail(
    database: str = Query(..., min_length=1),
    table: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mysql_config = await _load_mysql_config(db)
    from app.services.mcp_mysql import MCPMySQLClient

    client = MCPMySQLClient()
    columns = await client.describe_table(table, database, mysql_config)
    return {"columns": columns}
