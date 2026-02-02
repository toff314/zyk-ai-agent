"""
应用主模块
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, users, conversations, chat, config
from app.models.database import init_db, safe_commit
from app.utils.security import get_password_hash
from app.models.user import User
from app.models.config import Config
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="CSPM数据运营AI平台",
    description="基于LangChain和MCP的数据分析平台",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(config.router)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("应用启动中...")
    
    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")
    
    # 创建默认管理员用户（如果不存在）
    from app.models.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123!"),  # 默认密码，生产环境应修改
                role="admin"
            )
            db.add(admin)
            await safe_commit(db)
            logger.info("默认管理员用户创建成功 (用户名: admin, 密码: admin123!)")
        else:
            logger.info("管理员用户已存在")
        
        # 初始化默认配置（如果不存在）
        model_config_result = await db.execute(select(Config).where(Config.key == "model_config"))
        if not model_config_result.scalar_one_or_none():
            model_config = Config(
                key="model_config",
                value='{"api_key": "", "base_url": "https://open.bigmodel.cn/api/paas/v4/", "model": "glm-4"}'
            )
            db.add(model_config)
            logger.info("默认模型配置已创建")
        
        mysql_config_result = await db.execute(select(Config).where(Config.key == "mysql_config"))
        if not mysql_config_result.scalar_one_or_none():
            mysql_config = Config(
                key="mysql_config",
                value='{"enabled": false, "host": "", "port": 3306, "user": "", "password": "", "database": "", "timeout": 60}'
            )
            db.add(mysql_config)
            logger.info("默认MySQL配置已创建")
        
        gitlab_config_result = await db.execute(select(Config).where(Config.key == "gitlab_config"))
        if not gitlab_config_result.scalar_one_or_none():
            gitlab_config = Config(
                key="gitlab_config",
                value='{"url": "", "token": ""}'
            )
            db.add(gitlab_config)
            logger.info("默认GitLab配置已创建")
        
        await safe_commit(db)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用关闭中...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "CSPM数据运营AI平台API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
