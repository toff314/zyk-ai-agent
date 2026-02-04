"""
MySQL 元数据同步服务（基于 MCP MySQL 工具）
"""
import logging
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import safe_commit
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.services.mcp_mysql import MCPMySQLClient

logger = logging.getLogger(__name__)

SYSTEM_DATABASES = {"information_schema", "performance_schema", "mysql", "sys"}


async def sync_mysql_databases(
    db: AsyncSession,
    mysql_config: dict,
    client: MCPMySQLClient | None = None,
) -> list[dict]:
    """同步数据库列表到本地缓存表"""
    client = client or MCPMySQLClient()
    databases = await client.list_databases(mysql_config)
    existing = (
        await db.execute(select(MySQLDatabase))
    ).scalars().all()
    existing_map = {item.name: item for item in existing}

    await db.execute(delete(MySQLDatabase))
    for item in databases:
        name = item.get("database") or item.get("Database")
        if not name or name in SYSTEM_DATABASES:
            continue
        prev = existing_map.get(name)
        db.add(
            MySQLDatabase(
                name=name,
                remark=prev.remark if prev else None,
                enabled=prev.enabled if prev else True,
            )
        )
    await safe_commit(db)

    logger.info("同步MySQL数据库完成")
    return databases


async def sync_mysql_tables(
    db: AsyncSession,
    mysql_config: dict,
    database: str,
    client: MCPMySQLClient | None = None,
) -> list[dict]:
    """同步指定数据库的表列表到本地缓存表"""
    client = client or MCPMySQLClient()
    tables = await client.list_tables(database, mysql_config)
    existing = (
        await db.execute(
            select(MySQLTable).where(MySQLTable.database_name == database)
        )
    ).scalars().all()
    existing_map = {item.table_name: item for item in existing}

    await db.execute(delete(MySQLTable).where(MySQLTable.database_name == database))
    for item in tables:
        table_name = item.get("table_name") or ""
        prev = existing_map.get(table_name)
        db.add(
            MySQLTable(
                database_name=database,
                table_name=table_name,
                table_type=item.get("table_type") or "",
                table_comment=item.get("table_comment") or "",
                remark=prev.remark if prev else None,
                enabled=prev.enabled if prev else True,
            )
        )
    await safe_commit(db)

    logger.info("同步MySQL表完成: %s", database)
    return tables


async def sync_mysql_metadata(
    db: AsyncSession,
    mysql_config: dict,
    client: MCPMySQLClient | None = None,
) -> dict:
    """同步数据库与表元数据"""
    client = client or MCPMySQLClient()
    databases = await sync_mysql_databases(db, mysql_config, client=client)

    user_dbs = [
        item.get("database") or item.get("Database")
        for item in databases
        if (item.get("database") or item.get("Database")) not in SYSTEM_DATABASES
    ]

    table_count = 0
    for db_name in user_dbs:
        if not db_name:
            continue
        tables = await sync_mysql_tables(db, mysql_config, db_name, client=client)
        table_count += len(tables)

    return {"success": True, "database_count": len(user_dbs), "table_count": table_count}
