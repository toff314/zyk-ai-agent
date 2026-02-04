"""
数据库连接和会话管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import asyncio
import logging
from functools import wraps
from app.config.settings import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy基类"""
    pass


# 创建异步引擎 - 优化SQLite配置以避免数据库锁定
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    # SQLite特定配置
    connect_args={
        "check_same_thread": False,  # 允许多线程访问
        "timeout": 30  # 30秒锁定超时
    }
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def safe_commit(session: AsyncSession):
    """
    安全提交 - 自动重试数据库锁定错误
    
    参数:
        session: 数据库会话
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await session.commit()
            return
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                logger.warning(f"数据库锁定，第{attempt + 1}次重试提交...")
                await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避: 0.1s, 0.2s, 0.4s
            else:
                raise


async def get_db() -> AsyncSession:
    """
    依赖注入：获取数据库会话
    
    使用示例:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        # 导入所有模型以确保它们被注册
        from app.models.user import User
        from app.models.conversation import Conversation
        from app.models.message import Message
        from app.models.gitlab_user import GitLabUser
        from app.models.gitlab_project import GitLabProject
        from app.models.gitlab_branch import GitLabBranch
        from app.models.gitlab_commit import GitLabCommit
        from app.models.gitlab_commit_diff import GitLabCommitDiff
        from app.models.config import Config
        from app.models.mysql_database import MySQLDatabase
        from app.models.mysql_table import MySQLTable
        
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)


async def apply_sqlite_migrations():
    """为SQLite旧库补齐新增字段"""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    async with engine.begin() as conn:
        table_columns: dict[str, dict[str, str]] = {
            "gitlab_users": {
                "remark": "TEXT",
                "enabled": "INTEGER DEFAULT 1",
                "commits_week": "INTEGER DEFAULT 0",
                "commits_month": "INTEGER DEFAULT 0",
            },
            "gitlab_projects": {
                "remark": "TEXT",
                "enabled": "INTEGER DEFAULT 1",
            },
            "mysql_databases": {
                "remark": "TEXT",
                "enabled": "INTEGER DEFAULT 1",
            },
            "mysql_tables": {
                "remark": "TEXT",
                "enabled": "INTEGER DEFAULT 1",
            },
        }

        for table, columns in table_columns.items():
            result = await conn.execute(text(f"PRAGMA table_info('{table}')"))
            existing = {row._mapping["name"] for row in result}
            if not existing:
                continue
            for name, definition in columns.items():
                if name in existing:
                    continue
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def retry_on_locked(max_retries: int = 3, delay: float = 0.1):
    """
    重试装饰器 - 处理SQLite数据库锁定错误
    
    参数:
        max_retries: 最大重试次数，默认3次
        delay: 重试之间的延迟（秒），默认0.1秒
    
    使用示例:
        @retry_on_locked(max_retries=3)
        async def create_user(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"数据库锁定，第{attempt + 1}次重试...")
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                    else:
                        raise
            return None
        return wrapper
    return decorator
