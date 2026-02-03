"""
MySQL 元数据API
"""
import pymysql
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.database import get_db, safe_commit
from app.models.config import Config
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.middleware.auth import get_current_user
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


def _get_mysql_connection(mysql_config: dict):
    """创建MySQL连接（不指定默认数据库，以便查询所有数据库）"""
    return pymysql.connect(
        host=mysql_config.get("host"),
        port=mysql_config.get("port", 3306),
        user=mysql_config.get("user"),
        password=mysql_config.get("password"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


async def _sync_databases(db: AsyncSession, mysql_config: dict) -> list[dict]:
    """同步MySQL数据库列表"""
    conn = _get_mysql_connection(mysql_config)
    databases = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            result = cursor.fetchall()
            databases = [{"database": row.get('Database', '')} for row in result]
            logger.info(f"从MySQL获取到 {len(databases)} 个数据库")
    finally:
        conn.close()
    
    # 保存到本地数据库
    await db.execute(delete(MySQLDatabase))
    for item in databases:
        name = item.get("database") or item.get("Database")
        if not name or name in ['information_schema', 'performance_schema', 'mysql', 'sys']:
            continue
        db.add(MySQLDatabase(name=name))
    await safe_commit(db)
    
    logger.info(f"同步 {len([d for d in databases if d.get('database') not in ['information_schema', 'performance_schema', 'mysql', 'sys']])} 个用户数据库到本地")
    return databases


async def _sync_tables(db: AsyncSession, mysql_config: dict, database: str) -> list[dict]:
    """同步指定数据库的表列表"""
    conn = _get_mysql_connection(mysql_config)
    tables = []
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{database}'"
            cursor.execute(sql)
            result = cursor.fetchall()
            tables = [
                {
                    "table_name": row.get('TABLE_NAME', ''),
                    "table_type": row.get('TABLE_TYPE', ''),
                    "table_comment": row.get('TABLE_COMMENT', '')
                }
                for row in result
            ]
            logger.info(f"从MySQL数据库 {database} 获取到 {len(tables)} 个表")
    finally:
        conn.close()
    
    # 保存到本地数据库
    await db.execute(delete(MySQLTable).where(MySQLTable.database_name == database))
    for item in tables:
        db.add(
            MySQLTable(
                database_name=database,
                table_name=item.get("table_name") or "",
                table_type=item.get("table_type") or "",
                table_comment=item.get("table_comment") or "",
            )
        )
    await safe_commit(db)
    
    logger.info(f"同步 {len(tables)} 个表到本地数据库: {database}")
    return tables


@router.get("/databases")
async def list_mysql_databases(
    refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    获取数据库列表（可选刷新）
    """
    mysql_config = await _load_mysql_config(db)

    if refresh:
        await _sync_databases(db, mysql_config)

    result = await db.execute(select(MySQLDatabase).order_by(MySQLDatabase.name.asc()))
    items = result.scalars().all()

    if not items:
        await _sync_databases(db, mysql_config)
        result = await db.execute(select(MySQLDatabase).order_by(MySQLDatabase.name.asc()))
        items = result.scalars().all()

    return {
        "total": len(items),
        "items": [{"name": item.name} for item in items]
    }


@router.get("/tables")
async def list_mysql_tables(
    database: str = Query(..., min_length=1),
    refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    获取指定数据库的表列表（可选刷新）
    """
    mysql_config = await _load_mysql_config(db)

    if refresh:
        await _sync_tables(db, mysql_config, database)

    result = await db.execute(
        select(MySQLTable)
        .where(MySQLTable.database_name == database)
        .order_by(MySQLTable.table_name.asc())
    )
    items = result.scalars().all()

    if not items:
        await _sync_tables(db, mysql_config, database)
        result = await db.execute(
            select(MySQLTable)
            .where(MySQLTable.database_name == database)
            .order_by(MySQLTable.table_name.asc())
        )
        items = result.scalars().all()

    return {
        "total": len(items),
        "items": [
            {
                "database": item.database_name,
                "name": item.table_name,
                "type": item.table_type,
                "comment": item.table_comment
            }
            for item in items
        ]
    }
