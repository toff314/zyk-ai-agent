"""
对话历史API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List
from app.models.database import get_db, safe_commit
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/api/v1/conversations", tags=["对话历史"])


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    title: str
    mode: str
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    created_at: str


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: str
    mode: str  # normal, data_analysis, code_review


@router.get("", response_model=dict)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的对话列表
    
    参数:
        skip: 跳过的记录数
        limit: 返回的记录数
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 包含总数和对话列表
    """
    # 查询总数
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    )
    total = count_result.scalar()
    
    # 查询对话列表
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    # 获取每个对话的消息数量
    conversation_data = []
    for conv in conversations:
        msg_count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        message_count = msg_count_result.scalar()
        
        conversation_data.append({
            "id": conv.id,
            "title": conv.title,
            "mode": conv.mode,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "message_count": message_count
        })
    
    return {
        "total": total,
        "items": conversation_data
    }


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定对话的消息列表
    
    参数:
        conversation_id: 对话ID
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        List[MessageResponse]: 消息列表
    """
    # 验证对话是否属于当前用户
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权访问"
        )
    
    # 查询消息
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_data: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新对话
    
    参数:
        conv_data: 对话数据
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        ConversationResponse: 创建的对话信息
    """
    # 验证模式
    if conv_data.mode not in ["normal", "data_analysis", "code_review"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="模式必须是 normal, data_analysis 或 code_review"
        )
    
    # 创建对话
    new_conversation = Conversation(
        user_id=current_user.id,
        title=conv_data.title,
        mode=conv_data.mode
    )
    
    db.add(new_conversation)
    await safe_commit(db)
    await db.refresh(new_conversation)
    
    return {
        "id": new_conversation.id,
        "title": new_conversation.title,
        "mode": new_conversation.mode,
        "created_at": new_conversation.created_at.isoformat(),
        "updated_at": new_conversation.updated_at.isoformat(),
        "message_count": 0
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除对话（会级联删除所有消息）
    
    参数:
        conversation_id: 对话ID
        current_user: 当前登录用户
        db: 数据库会话
    
    返回:
        dict: 删除结果
    """
    # 验证对话是否属于当前用户
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权访问"
        )
    
    # 删除对话（会级联删除消息）
    await db.delete(conversation)
    await safe_commit(db)
    
    return {"message": "对话删除成功"}
