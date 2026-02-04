"""
对话交互API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, safe_commit
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.config import Config
from app.models.mysql_database import MySQLDatabase
from app.models.mysql_table import MySQLTable
from app.models.gitlab_user import GitLabUser
from app.middleware.auth import get_current_user
from app.services.agent_service import AgentFactory
import re
import json
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/chat", tags=["对话交互"])


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    mode: str  # normal, data_analysis, code_review
    conversation_id: Optional[int] = None
    review_diff: Optional[str] = None
    review_notice: Optional[str] = None


class ChatResponse(BaseModel):
    """对话响应"""
    type: str  # chunk, done, error
    content: Optional[str] = None
    error: Optional[str] = None


AT_TOKEN_PATTERN = re.compile(r'@([\u4e00-\u9fffA-Za-z0-9_]+)')


def _clean_message_remove_at_tokens(message: str) -> str:
    cleaned = AT_TOKEN_PATTERN.sub("", message)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build_db_table_context(tokens: list[str]) -> dict:
    pairs: list[tuple[str, Optional[str]]] = []
    i = 0
    while i < len(tokens):
        database = tokens[i]
        table = tokens[i + 1] if i + 1 < len(tokens) else None
        pairs.append((database, table))
        i += 2 if table else 1

    db_to_tables: dict[str, list[str]] = {}
    db_order: list[str] = []
    table_order: list[str] = []

    for database, table in pairs:
        if database not in db_to_tables:
            db_to_tables[database] = []
            db_order.append(database)
        if table:
            if table not in db_to_tables[database]:
                db_to_tables[database].append(table)
            if table not in table_order:
                table_order.append(table)

    return {
        "databases": db_order,
        "tables": table_order,
        "mapping": db_to_tables,
    }


def _parse_db_table_mentions(message: str) -> tuple[Optional[dict], str]:
    tokens = [match.group(1) for match in AT_TOKEN_PATTERN.finditer(message)]
    if not tokens:
        return None, message

    context = _build_db_table_context(tokens)
    cleaned_message = _clean_message_remove_at_tokens(message)
    return context, cleaned_message


def _build_db_table_prompt(context: dict, user_message: str) -> str:
    payload = json.dumps(context, ensure_ascii=False)
    if not user_message:
        user_message = "请根据上述数据库/表信息完成用户请求。"
    return f"[DB_TABLE_CONTEXT]\n{payload}\n[/DB_TABLE_CONTEXT]\n\n用户问题：{user_message}"


async def _resolve_db_table_mentions(db: AsyncSession, message: str) -> tuple[Optional[dict], str]:
    tokens = [match.group(1) for match in AT_TOKEN_PATTERN.finditer(message)]
    if not tokens:
        return None, message

    db_rows = (
        await db.execute(select(MySQLDatabase).where(MySQLDatabase.enabled.is_(True)))
    ).scalars().all()
    table_rows = (
        await db.execute(select(MySQLTable).where(MySQLTable.enabled.is_(True)))
    ).scalars().all()

    db_alias_map: dict[str, str] = {}
    for row in db_rows:
        if row.name:
            db_alias_map[row.name] = row.name
        if row.remark:
            db_alias_map[row.remark] = row.name

    tables_by_db: dict[str, dict[str, str]] = {}
    for table in table_rows:
        if table.database_name not in tables_by_db:
            tables_by_db[table.database_name] = {}
        if table.table_name:
            tables_by_db[table.database_name][table.table_name] = table.table_name
        if table.remark:
            tables_by_db[table.database_name][table.remark] = table.table_name

    mapped_tokens: list[str] = []
    current_db: Optional[str] = None
    for token in tokens:
        if token in db_alias_map:
            current_db = db_alias_map[token]
            mapped_tokens.append(current_db)
            continue
        if current_db and token in tables_by_db.get(current_db, {}):
            mapped_tokens.append(tables_by_db[current_db][token])
            continue

    if not mapped_tokens:
        return None, _clean_message_remove_at_tokens(message)

    context = _build_db_table_context(mapped_tokens)
    cleaned_message = _clean_message_remove_at_tokens(message)
    return context, cleaned_message


async def _resolve_gitlab_mentions(db: AsyncSession, message: str) -> str:
    tokens = [match.group(1) for match in AT_TOKEN_PATTERN.finditer(message)]
    if not tokens:
        return message

    users = (
        await db.execute(select(GitLabUser).where(GitLabUser.enabled.is_(True)))
    ).scalars().all()
    alias_map: dict[str, str] = {}
    for user in users:
        if user.username:
            alias_map[user.username] = user.username
        if user.name:
            alias_map[user.name] = user.username
        if user.remark:
            alias_map[user.remark] = user.username

    def _replace(match: re.Match) -> str:
        token = match.group(1)
        actual = alias_map.get(token)
        if not actual:
            return ""
        return f"@{actual}"

    cleaned = AT_TOKEN_PATTERN.sub(_replace, message)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


async def process_message(
    message: str,
    mode: str,
    db: AsyncSession,
    review_diff: Optional[str] = None,
    review_notice: Optional[str] = None,
) -> str:
    """
    处理消息并返回响应
    
    参数:
        message: 用户消息
        mode: 对话模式
        db: 数据库会话
    
    返回:
        str: AI响应内容
    """
    try:
        # 获取模型配置
        config_result = await db.execute(select(Config).where(Config.key == "model_config"))
        config = config_result.scalar_one_or_none()
        
        if not config:
            return "请先配置模型API信息"
        
        model_config = json.loads(config.value)
        
        system_prompt = None

        # 解析 @ 库/表，仅在数据分析模式生效
        if mode == "data_analysis":
            context, cleaned_message = await _resolve_db_table_mentions(db, message)
            if context:
                message = _build_db_table_prompt(context, cleaned_message)
        elif mode == "code_review":
            message = await _resolve_gitlab_mentions(db, message)
            if review_diff is not None or review_notice is not None:
                from app.utils.code_review_prompt import render_code_review_prompt
                system_prompt = render_code_review_prompt(review_diff or "", review_notice)

        # 创建并使用Agent
        agent = await AgentFactory.create_agent(mode, model_config, system_prompt=system_prompt)
        response = await agent.query(message)
        
        return response
            
    except Exception as e:
        logger.error(f"处理消息失败: {str(e)}")
        return f"处理失败: {str(e)}"


def extract_sql_query(message: str) -> Optional[str]:
    """
    从消息中提取SQL查询
    
    参数:
        message: 用户消息
    
    返回:
        Optional[str]: SQL查询语句
    """
    # 查找SQL代码块
    sql_match = re.search(r'```sql\s*(.*?)\s*```', message, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # 查找SELECT语句
    select_match = re.search(r'SELECT.*?(?:;|$)', message, re.IGNORECASE | re.DOTALL)
    if select_match:
        return select_match.group(0).strip()
    
    return None


@router.post("/stream")
async def chat_stream(
    chat_data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    流式对话接口
    
    参数:
        chat_data: 对话数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        StreamingResponse: 流式响应
    """
    # 验证模式
    if chat_data.mode not in ["normal", "data_analysis", "code_review"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的对话模式"
        )
    
    # 获取或创建对话
    if chat_data.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == chat_data.conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
    else:
        # 创建新对话
        conversation = Conversation(
            user_id=current_user.id,
            title=chat_data.message[:50],  # 使用消息前50字符作为标题
            mode=chat_data.mode
        )
        db.add(conversation)
        await safe_commit(db)
        await db.refresh(conversation)
    
    # 保存用户消息
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=chat_data.message
    )
    db.add(user_message)
    
    # 处理消息
    try:
        response_content = await process_message(
            chat_data.message,
            chat_data.mode,
            db,
            review_diff=chat_data.review_diff,
            review_notice=chat_data.review_notice,
        )
        
        # 保存AI响应
        ai_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_content
        )
        db.add(ai_message)
        await safe_commit(db)
        
        # 流式响应
        async def generate():
            # 发送对话ID
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation.id})}\n\n"
            
            # 分块发送内容（模拟流式输出）
            chunks = [response_content[i:i+100] for i in range(0, len(response_content), 100)]
            for chunk in chunks:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"处理对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理对话失败: {str(e)}"
        )


@router.get("/gitlab/users")
async def get_gitlab_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取GitLab用户列表（用于@符号选择）
    
    参数:
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        list: GitLab用户列表
    """
    try:
        from app.models.gitlab_user import GitLabUser

        result = await db.execute(
            select(GitLabUser)
            .where(GitLabUser.enabled.is_(True))
            .order_by(GitLabUser.name.asc())
        )
        users = result.scalars().all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "remark": user.remark,
                "enabled": user.enabled,
                "commits_week": user.commits_week,
                "commits_month": user.commits_month,
            }
            for user in users
        ]
    except Exception as e:
        logger.error(f"获取GitLab用户失败: {str(e)}")
        return []


@router.get("/stats")
async def get_chat_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取聊天统计信息
    
    参数:
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 统计信息
    """
    try:
        # 统计对话数量
        conv_result = await db.execute(
            select(Conversation).where(Conversation.user_id == current_user.id)
        )
        conversations = conv_result.scalars().all()
        
        # 统计消息数量
        msg_result = await db.execute(
            select(Message)
            .join(Conversation)
            .where(Conversation.user_id == current_user.id)
        )
        messages = msg_result.scalars().all()
        
        return {
            "total_conversations": len(conversations),
            "total_messages": len(messages),
            "conversations_by_mode": {
                "normal": len([c for c in conversations if c.mode == "normal"]),
                "data_analysis": len([c for c in conversations if c.mode == "data_analysis"]),
                "code_review": len([c for c in conversations if c.mode == "code_review"]),
            }
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )
