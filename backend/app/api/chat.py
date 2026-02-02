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


class ChatResponse(BaseModel):
    """对话响应"""
    type: str  # chunk, done, error
    content: Optional[str] = None
    error: Optional[str] = None


async def process_message(message: str, mode: str, db: AsyncSession) -> str:
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
        
        # 创建并使用Agent
        agent = await AgentFactory.create_agent(mode, model_config)
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
        response_content = await process_message(chat_data.message, chat_data.mode, db)
        
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
    from app.services.gitlab import gitlab_service
    
    if not gitlab_service:
        return []
    
    try:
        users = await gitlab_service.get_all_users(db)
        return users
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
