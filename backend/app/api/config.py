"""
配置管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.models.database import get_db, safe_commit
from app.models.user import User
from app.models.config import Config
from app.middleware.auth import get_current_user
import json
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/config", tags=["配置管理"])


class ModelConfigRequest(BaseModel):
    """模型配置请求"""
    api_key: str
    base_url: str
    model: str


class GitLabConfigRequest(BaseModel):
    """GitLab配置请求"""
    url: str
    token: str


class MySQLConfigRequest(BaseModel):
    """MySQL配置请求"""
    host: str
    port: int
    user: str
    password: str
    database: str


@router.get("")
async def get_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有配置
    
    参数:
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 配置信息
    """
    try:
        config = {}
        
        # 获取模型配置
        model_config_result = await db.execute(
            select(Config).where(Config.key == "model_config")
        )
        model_config = model_config_result.scalar_one_or_none()
        if model_config:
            config["model_config"] = json.loads(model_config.value)
        
        # 获取GitLab配置
        gitlab_config_result = await db.execute(
            select(Config).where(Config.key == "gitlab_config")
        )
        gitlab_config = gitlab_config_result.scalar_one_or_none()
        if gitlab_config:
            config["gitlab_config"] = json.loads(gitlab_config.value)
        
        # 获取MCP配置
        mcp_config_result = await db.execute(
            select(Config).where(Config.key == "mcp_config")
        )
        mcp_config = mcp_config_result.scalar_one_or_none()
        if mcp_config:
            config["mcp_config"] = json.loads(mcp_config.value)
        
        return {"code": 0, "data": config}
        
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


@router.put("/model")
async def update_model_config(
    config_data: ModelConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新模型配置
    
    参数:
        config_data: 模型配置数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 更新结果
    """
    # 只有管理员可以修改配置
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以修改配置"
        )
    
    try:
        # 查找现有配置
        result = await db.execute(
            select(Config).where(Config.key == "model_config")
        )
        config = result.scalar_one_or_none()
        
        config_value = {
            "api_key": config_data.api_key,
            "base_url": config_data.base_url,
            "model": config_data.model
        }
        
        if config:
            # 更新现有配置
            config.value = json.dumps(config_value)
        else:
            # 创建新配置
            config = Config(
                key="model_config",
                value=json.dumps(config_value)
            )
            db.add(config)
        
        await safe_commit(db)
        await db.refresh(config)
        
        return {"code": 0, "message": "模型配置更新成功"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"更新模型配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型配置失败: {str(e)}"
        )


@router.put("/gitlab")
async def update_gitlab_config(
    config_data: GitLabConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新GitLab配置
    
    参数:
        config_data: GitLab配置数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 更新结果
    """
    # 只有管理员可以修改配置
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以修改配置"
        )
    
    try:
        # 查找现有配置
        result = await db.execute(
            select(Config).where(Config.key == "gitlab_config")
        )
        config = result.scalar_one_or_none()
        
        config_value = {
            "url": config_data.url,
            "token": config_data.token
        }
        
        if config:
            # 更新现有配置
            config.value = json.dumps(config_value)
        else:
            # 创建新配置
            config = Config(
                key="gitlab_config",
                value=json.dumps(config_value)
            )
            db.add(config)
        
        await safe_commit(db)
        await db.refresh(config)
        
        return {"code": 0, "message": "GitLab配置更新成功"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"更新GitLab配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新GitLab配置失败: {str(e)}"
        )


@router.put("/mysql")
async def update_mysql_config(
    config_data: MySQLConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新MySQL配置
    
    参数:
        config_data: MySQL配置数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 更新结果
    """
    # 只有管理员可以修改配置
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以修改配置"
        )
    
    try:
        # 查找现有配置
        result = await db.execute(
            select(Config).where(Config.key == "mysql_config")
        )
        config = result.scalar_one_or_none()
        
        config_value = {
            "host": config_data.host,
            "port": config_data.port,
            "user": config_data.user,
            "password": config_data.password,
            "database": config_data.database
        }
        
        config_value["enabled"] = True
        config_value["timeout"] = 60
        
        if config:
            # 更新现有配置
            config.value = json.dumps(config_value)
        else:
            # 创建新配置
            config = Config(
                key="mysql_config",
                value=json.dumps(config_value)
            )
            db.add(config)
        
        await safe_commit(db)
        await db.refresh(config)
        
        # 同步元数据
        sync_result = {"success": True, "message": "同步成功"}
        try:
            from app.api.mysql_metadata import _sync_databases, _sync_tables
            
            mysql_config = {
                "host": config_data.host,
                "port": config_data.port,
                "user": config_data.user,
                "password": config_data.password,
                "database": config_data.database
            }
            
            logger.info("开始同步MySQL元数据...")
            
            # 同步数据库列表
            databases = await _sync_databases(db, mysql_config)
            
            # 过滤掉系统数据库
            user_db_count = len([d for d in databases if d.get('database') not in ['information_schema', 'performance_schema', 'mysql', 'sys']])
            
            # 同步每个数据库的表
            table_count = 0
            for db_obj in databases:
                db_name = db_obj.get("database")
                if not db_name or db_name in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                    continue
                try:
                    tables = await _sync_tables(db, mysql_config, db_name)
                    table_count += len(tables)
                except Exception as e:
                    logger.warning(f"同步数据库 {db_name} 的表失败: {e}")
            
            sync_result["message"] = f"同步成功: {user_db_count} 个数据库, {table_count} 个表"
            logger.info(f"同步完成: {user_db_count} 个数据库, {table_count} 个表")
        except Exception as sync_error:
            logger.error(f"同步MySQL元数据失败: {str(sync_error)}", exc_info=True)
            sync_result = {
                "success": False,
                "message": f"同步失败: {str(sync_error)}"
            }
        
        return {
            "code": 1 if not sync_result["success"] else 0,
            "message": "MySQL配置更新成功",
            "sync": sync_result
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"更新MySQL配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新MySQL配置失败: {str(e)}"
        )


@router.post("/test/model")
async def test_model_config(
    config_data: ModelConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    测试模型配置 - 使用OpenAI兼容接口
    
    参数:
        config_data: 模型配置数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 测试结果
    """
    # 只有管理员可以测试配置
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以测试配置"
        )
    
    try:
        from langchain_openai import ChatOpenAI
        import asyncio
        
        logger.info(f"开始测试模型配置: {config_data.model}")
        logger.info(f"使用base_url: {config_data.base_url}")
        
        # 创建LLM实例，添加超时设置
        # ChatOpenAI会自动在base_url后添加/chat/completions
        llm = ChatOpenAI(
            api_key=config_data.api_key,
            base_url=config_data.base_url.rstrip('/'),
            model=config_data.model,
            temperature=0.7,
            max_tokens=50,  # 测试时返回适量token
            request_timeout=30.0,  # 设置30秒超时
        )
        
        # 发送测试请求，带超时
        response = await asyncio.wait_for(
            llm.ainvoke("你好，请回复'测试成功'"),
            timeout=30.0
        )
        
        logger.info(f"模型响应成功: {response.content[:100]}")
        
        return {
            "code": 0,
            "message": "模型配置测试成功",
            "data": {
                "response": response.content[:200]  # 返回前200个字符
            }
        }
        
    except asyncio.TimeoutError:
        logger.error("测试模型配置超时")
        return {
            "code": -1,
            "message": "测试失败: 请求超时，请检查网络连接或API地址是否正确"
        }
    except Exception as e:
        logger.error(f"测试模型配置失败: {str(e)}", exc_info=True)
        return {
            "code": -1,
            "message": f"测试失败: {str(e)}",
            "error_detail": str(e)
        }


@router.post("/test/mysql")
async def test_mysql_config(
    config_data: MySQLConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    测试MySQL配置连接
    
    参数:
        config_data: MySQL配置数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 测试结果
    """
    # 只有管理员可以测试配置
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以测试配置"
        )
    
    try:
        from app.services.mcp_mysql import MCPMySQLClient
        
        mysql_config = {
            "host": config_data.host,
            "port": config_data.port,
            "user": config_data.user,
            "password": config_data.password,
            "database": config_data.database
        }
        
        logger.info(f"开始测试MySQL配置: {config_data.host}:{config_data.port}")
        
        # 尝试连接并查询数据库列表
        client = MCPMySQLClient()
        databases = await client.list_databases(mysql_config)
        
        logger.info(f"MySQL连接成功，找到 {len(databases)} 个数据库")

        table_count = 0
        for db_info in databases:
            db_name = db_info.get("database") or db_info.get("Database")
            if not db_name:
                continue
            logger.info(f"数据库: {db_name}")
            tables = await client.list_tables(db_name, mysql_config)
            table_count += len(tables)
            logger.info(f"数据库 {db_name}: {len(tables)} 个表")
        
        logger.info(f"共 {table_count} 个表")
        
        
        return {
            "code": 0,
            "message": "MySQL连接测试成功",
            "data": {
                "database_count": len(databases),
                "table_count": table_count
            }
        }
        
    except Exception as e:
        logger.error(f"测试MySQL配置失败: {str(e)}", exc_info=True)
        return {
            "code": -1,
            "message": f"测试失败: {str(e)}",
            "error_detail": str(e)
        }
